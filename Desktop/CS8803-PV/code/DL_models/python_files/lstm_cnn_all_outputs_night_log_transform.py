#!/usr/bin/env python3
# -- coding: utf-8 --

# Same as lstm_cnn_all_outputs_night.py, but log1p transform on key skewed variables
# (distribution plots). Saves under lstm and cnn images night log_transform/

import os
import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler

from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import *
from tensorflow.keras.callbacks import ModelCheckpoint, ReduceLROnPlateau
from tensorflow.keras.losses import MeanSquaredError
from tensorflow.keras.metrics import RootMeanSquaredError
from tensorflow.keras.optimizers import AdamW
from tensorflow.keras.regularizers import l2

import matplotlib.pyplot as plt
import seaborn as sns

import time

# Variables with heavy-tailed / skewed distributions (log1p before modeling)
LOG_TRANSFORM_COLS = [
    'MonoSi_Power',
    'PolySi_Power',
    'TFSi_a_Power',
    'TFcigs_Power',
    'GlobalIR',
    'DiffuseIR',
    'DirectIR',
]

# Output columns to predict (same as distribution_outputs)
OUTPUT_COLUMNS = [
    'MonoSi_Power',
    'PolySi_Power',
    'TFSi_a_Power',
    'TFcigs_Power',
    'GlobalIR',
    'DiffuseIR',
    'DirectIR',
]

# Input columns per output type (avoid using the target as input)
INPUT_COLUMNS_MAP = {
    'MonoSi_Power': ['CosDayOfYear', 'SinDayOfYear', 'CosSeconds', 'SinSeconds',
                    'MonoSi_Vin', 'MonoSi_Iin', 'MonoSi_Vout', 'MonoSi_Iout',
                    'Temp_Mono', 'GlobalIR'],
    'PolySi_Power': ['CosDayOfYear', 'SinDayOfYear', 'CosSeconds', 'SinSeconds',
                     'PolySi_Vin', 'PolySi_Iin', 'PolySi_Vout', 'PolySi_Iout',
                     'Temp_Poly', 'GlobalIR'],
    'TFSi_a_Power': ['CosDayOfYear', 'SinDayOfYear', 'CosSeconds', 'SinSeconds',
                     'TFSi_a_Vin', 'TFSi_a_Iin', 'TFSi_a_Vout', 'TFSi_a_Iout',
                     'Temp_Amor', 'GlobalIR'],
    'TFcigs_Power': ['CosDayOfYear', 'SinDayOfYear', 'CosSeconds', 'SinSeconds',
                     'TFcigs_Vin', 'TFcigs_Iin', 'TFcigs_Vout', 'TFcigs_Iout',
                     'Temp_Cigs', 'GlobalIR'],
    'GlobalIR': ['CosDayOfYear', 'SinDayOfYear', 'CosSeconds', 'SinSeconds',
                 'WindSpeed', 'Temperature', 'DiffuseIR', 'DirectIR'],
    'DiffuseIR': ['CosDayOfYear', 'SinDayOfYear', 'CosSeconds', 'SinSeconds',
                  'WindSpeed', 'Temperature', 'GlobalIR', 'DirectIR'],
    'DirectIR': ['CosDayOfYear', 'SinDayOfYear', 'CosSeconds', 'SinSeconds',
                 'WindSpeed', 'Temperature', 'GlobalIR', 'DiffuseIR'],
}

WINDOW_SIZE = 50
EPOCHS = 20


def apply_log1p_columns(df):
    """In-place log1p on LOG_TRANSFORM_COLS (clamps negatives to 0 for safety)."""
    for c in LOG_TRANSFORM_COLS:
        if c not in df.columns:
            continue
        x = df[c].to_numpy(dtype=np.float64, copy=True)
        np.maximum(x, 0.0, out=x)
        df[c] = np.log1p(x)


def get_column_indices(df, columns):
    return [df.columns.get_loc(col) for col in columns]


def lists_to_indices(df, inputs_list, outputs_list):
    input_indices = get_column_indices(df, inputs_list)
    output_indices = get_column_indices(df, outputs_list)
    return input_indices, output_indices


def df_to_X_y3(df, window_size, input_indices, output_indices):
    df_as_np = df.to_numpy()
    X, y = [], []
    for i in range(len(df_as_np) - window_size):
        X.append(df_as_np[i:i + window_size, input_indices])
        y.append(df_as_np[i + window_size, output_indices])
    return np.array(X), np.array(y)


def build_model(window_size, n_inputs, n_outputs):
    model = Sequential()
    model.add(InputLayer((window_size, n_inputs)))
    model.add(Conv1D(64, 3, activation='relu', padding='same', kernel_regularizer=l2(0.001)))
    model.add(BatchNormalization())
    model.add(Dropout(0.2))
    model.add(Conv1D(128, 3, activation='relu', padding='same', kernel_regularizer=l2(0.001)))
    model.add(BatchNormalization())
    model.add(Dropout(0.2))
    model.add(Conv1D(64, 2, activation='relu', padding='same', kernel_regularizer=l2(0.001)))
    model.add(BatchNormalization())
    model.add(Dropout(0.2))
    model.add(LSTM(256, return_sequences=True, kernel_regularizer=l2(0.001)))
    model.add(Dropout(0.3))
    model.add(LSTM(128, kernel_regularizer=l2(0.001)))
    model.add(Dropout(0.3))
    model.add(Dense(64, activation='relu', kernel_regularizer=l2(0.001)))
    model.add(Dense(32, activation='relu', kernel_regularizer=l2(0.001)))
    model.add(Dense(16, activation='relu', kernel_regularizer=l2(0.001)))
    model.add(Dense(2, activation='linear'))
    model.add(Dense(n_outputs, activation='linear'))
    return model


def split_time_series(df, train_frac=0.70, val_frac=0.15):
    df = df.sort_values('date').reset_index(drop=True)
    n = len(df)
    train_end = int(n * train_frac)
    val_end = int(n * (train_frac + val_frac))
    training_data = df.iloc[:train_end].copy()
    validation_data = df.iloc[train_end:val_end].copy()
    testing_data = df.iloc[val_end:].copy()
    return training_data, validation_data, testing_data


def train_and_evaluate(output_col, df_train, training_data, validation_data, testing_data,
                       images_base_folder):
    """Train CNN-LSTM for one output and save results."""
    input_columns = INPUT_COLUMNS_MAP.get(output_col)
    if not input_columns:
        print(f"  Skipping {output_col}: no input mapping")
        return

    # Check all columns exist
    missing = [c for c in input_columns + [output_col] if c not in df_train.columns]
    if missing:
        print(f"  Skipping {output_col}: missing columns {missing}")
        return

    output_folder = os.path.join(images_base_folder, output_col.replace(' ', '_'))
    os.makedirs(output_folder, exist_ok=True)

    input_indices, output_indices = lists_to_indices(df_train, input_columns, [output_col])

    X_train, y_train = df_to_X_y3(training_data, WINDOW_SIZE, input_indices, output_indices)
    X_val, y_val = df_to_X_y3(validation_data, WINDOW_SIZE, input_indices, output_indices)
    X_test, y_test = df_to_X_y3(testing_data, WINDOW_SIZE, input_indices, output_indices)

    scaler_X = StandardScaler()
    scaler_y = StandardScaler()
    X_train_scaled = scaler_X.fit_transform(X_train.reshape(-1, X_train.shape[-1])).reshape(X_train.shape)
    y_train_scaled = scaler_y.fit_transform(y_train)
    X_val_scaled = scaler_X.transform(X_val.reshape(-1, X_val.shape[-1])).reshape(X_val.shape)
    y_val_scaled = scaler_y.transform(y_val)
    X_test_scaled = scaler_X.transform(X_test.reshape(-1, X_test.shape[-1])).reshape(X_test.shape)
    y_test_scaled = scaler_y.transform(y_test)

    print(f"  Tensors: X_train {X_train.shape}, y_train {y_train.shape} | "
          f"X_val {X_val.shape} | X_test {X_test.shape}")
    model = build_model(WINDOW_SIZE, len(input_columns), 1)
    ckpt_path = os.path.join(output_folder, 'best_model.keras')
    cp = ModelCheckpoint(ckpt_path, save_best_only=True)
    reduce_lr = ReduceLROnPlateau(
        monitor='val_loss', factor=0.5, patience=2, min_lr=1e-6, verbose=1
    )
    optimizer = AdamW(learning_rate=0.001, weight_decay=0.0001)
    model.compile(loss=MeanSquaredError(), optimizer=optimizer, metrics=[RootMeanSquaredError()])
    model.summary()

    history = model.fit(
        X_train_scaled, y_train_scaled,
        validation_data=(X_val_scaled, y_val_scaled),
        epochs=EPOCHS, batch_size=128, callbacks=[cp, reduce_lr], verbose=1
    )

    hist_df = pd.DataFrame(history.history)
    hist_df.insert(0, 'epoch', np.arange(1, len(hist_df) + 1))
    print(f"\n  --- Historique par époque ({output_col}) ---")
    with pd.option_context('display.max_columns', None, 'display.width', 200):
        print(hist_df.to_string(index=False, float_format=lambda x: f'{x:.6f}'))

    # Load best model (lowest val_loss) for test evaluation
    model = load_model(ckpt_path)

    predictions = model.predict(X_test_scaled, verbose=1)

    # Metrics in scaled space (same as Keras training target)
    mse_scaled = mean_squared_error(y_test_scaled, predictions)
    rmse_scaled = np.sqrt(mse_scaled)
    mae_scaled = mean_absolute_error(y_test_scaled, predictions)
    r2_scaled = r2_score(y_test_scaled, predictions)

    # Original-scale metrics: inverse StandardScaler then expm1 (log1p was applied in CSV prep)
    y_test_log = scaler_y.inverse_transform(y_test_scaled)
    pred_log = scaler_y.inverse_transform(predictions)
    y_orig = np.expm1(y_test_log)
    pred_orig = np.expm1(pred_log)
    mse = mean_squared_error(y_orig, pred_orig)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(y_orig, pred_orig)
    r2 = r2_score(y_orig, pred_orig)

    # Save RMSE evolution
    plt.figure(figsize=(10, 6))
    epochs_range = range(1, len(history.history['root_mean_squared_error']) + 1)
    plt.plot(epochs_range, history.history['root_mean_squared_error'], 'b-o', markersize=4, label='Training RMSE')
    plt.plot(epochs_range, history.history['val_root_mean_squared_error'], 'r-s', markersize=4, label='Validation RMSE')
    plt.xlabel('Epoch')
    plt.ylabel('RMSE')
    plt.title(f'RMSE over Epochs - {output_col} (CNN-LSTM, log1p targets)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(output_folder, 'rmse_evolution.png'), dpi=150)
    plt.close()

    # Save actual vs predicted (original physical units)
    plt.figure(figsize=(12, 6))
    yo, po = y_orig.flatten(), pred_orig.flatten()
    sns.scatterplot(x=yo, y=po, alpha=0.5, label='Predicted vs Actual')
    sns.regplot(x=yo, y=po, scatter=False, color='blue', label='Regression Line')
    lo, hi = float(np.min(yo)), float(np.max(yo))
    plt.plot([lo, hi], [lo, hi], 'r--', label='Perfect Prediction')
    plt.xlabel(f'Actual {output_col} (original scale, expm1)')
    plt.ylabel(f'Predicted {output_col} (original scale, expm1)')
    plt.title(f'Actual vs Predicted {output_col} (CNN-LSTM, log1p train)')
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(output_folder, 'actual_vs_predicted.png'), dpi=150)
    plt.close()

    # Save results TXT
    txt_path = os.path.join(output_folder, 'results.txt')
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(f"CNN-LSTM Results for {output_col} (log1p on: {', '.join(LOG_TRANSFORM_COLS)})\n")
        f.write("=" * 50 + "\n\n")
        f.write("Epochs (Training RMSE, Validation RMSE) — scaled log1p target space:\n")
        for i, (tr, val) in enumerate(zip(history.history['root_mean_squared_error'],
                                           history.history['val_root_mean_squared_error']), 1):
            f.write(f"  Epoch {i:3d}: train_rmse={tr:.4f}, val_rmse={val:.4f}\n")
        f.write("\nTest metrics (scaled log1p space, after StandardScaler on y):\n")
        f.write(f"  RMSE:  {rmse_scaled:.4f}\n")
        f.write(f"  MAE:   {mae_scaled:.4f}\n")
        f.write(f"  R²:    {r2_scaled:.4f}\n")
        f.write("\nTest metrics (original physical units, expm1 after inverse scaler):\n")
        f.write(f"  RMSE:  {rmse:.4f}\n")
        f.write(f"  MAE:   {mae:.4f}\n")
        f.write(f"  R²:    {r2:.4f}\n")

    print(f"  Test {output_col} (échelle d'origine, expm1): RMSE={rmse:.4f}, MAE={mae:.4f}, R²={r2:.4f} -> {output_folder}")


def main():
    starttime = time.time()
    train_path = "../combined_files/prediction/deger/bag_1h_24h_with_night_2020_2025.csv"
    df_train = pd.read_csv(train_path)
    df_train['date'] = pd.to_datetime(df_train['date'])
    df_train = df_train.sort_values('date').reset_index(drop=True)

    apply_log1p_columns(df_train)
    print("log1p appliqué aux colonnes:", [c for c in LOG_TRANSFORM_COLS if c in df_train.columns], "\n")

    training_data, validation_data, testing_data = split_time_series(df_train)

    print("Données d'entraînement:", len(training_data), "lignes |",
          training_data['date'].min(), "->", training_data['date'].max())
    print(training_data.head(), "\n")
    print("Données de validation:", len(validation_data), "lignes |",
          validation_data['date'].min(), "->", validation_data['date'].max())
    print(validation_data.head(), "\n")
    print("Données de test:", len(testing_data), "lignes |",
          testing_data['date'].min(), "->", testing_data['date'].max())
    print(testing_data.head(), "\n")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    images_base_folder = os.path.join(
        os.path.dirname(script_dir), "lstm and cnn images night log_transform 2020_2025"
    )
    os.makedirs(images_base_folder, exist_ok=True)
    print(f"Dossier sortie: {images_base_folder}\n")

    for output_col in OUTPUT_COLUMNS:
        print(f"Training for {output_col}...")
        train_and_evaluate(output_col, df_train, training_data, validation_data, testing_data, images_base_folder)

    print(f"\nTotal runtime: {time.time() - starttime:.1f} seconds")


if __name__ == "__main__":
    main()
