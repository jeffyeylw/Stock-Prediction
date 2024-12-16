import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error
from keras.models import Sequential
from keras.layers import LSTM, Dropout, Dense
import yfinance as yf

# Import stock data from Yahoo Finance
aapl = yf.download("aapl", start="2022-01-01", end="2023-11-10", interval="1h")

# Visualize the closing price
plt.figure(figsize=(15, 5))
aapl['Adj Close'].plot()
plt.title('Historical Closing Price of AAPL')
plt.xlabel('Date')
plt.ylabel('Adj Close')
plt.show()

# Visualize the trading volume
plt.figure(figsize=(15, 5))
aapl['Volume'].plot()
plt.title('Trading Volume for AAPL')
plt.xlabel('Date')
plt.ylabel('Volume')
plt.show()

# Feature scaling
close_val = aapl['Close'].values.reshape(-1, 1)
scaler = MinMaxScaler(feature_range=(0, 1))
scaled_data = scaler.fit_transform(close_val)

# Prepare training and test data
train_size = int(len(scaled_data) * 0.8)
train_data = scaled_data[:train_size, :]
test_data = scaled_data[train_size:, :]

x_train, y_train = [], []
for i in range(60, len(train_data)):
    x_train.append(train_data[i-60:i, 0])
    y_train.append(train_data[i, 0])
x_train, y_train = np.array(x_train), np.array(y_train)
x_train = np.reshape(x_train, (x_train.shape[0], x_train.shape[1], 1))

x_test, y_test = [], close_val[train_size+60:]
for i in range(60, len(test_data)):
    x_test.append(test_data[i-60:i, 0])
x_test = np.array(x_test)
x_test = np.reshape(x_test, (x_test.shape[0], x_test.shape[1], 1))

# Build the LSTM model
model = Sequential()
model.add(LSTM(units=50, return_sequences=True, input_shape=(x_train.shape[1], 1)))
model.add(Dropout(0.2))
model.add(LSTM(units=50, return_sequences=True))
model.add(Dropout(0.2))
model.add(LSTM(units=50))
model.add(Dropout(0.2))
model.add(Dense(units=1))

model.compile(optimizer='adam', loss='mean_squared_error')

# Train the model
model.fit(x_train, y_train, epochs=100, batch_size=32, verbose=1)

# Predicting the prices
predicted_prices = model.predict(x_test)
predicted_prices = scaler.inverse_transform(predicted_prices)

# Reformat the data for MSE calculation
date_index = aapl.index[train_size+60:train_size+60+len(predicted_prices)]
predicted_prices_df = pd.DataFrame(predicted_prices, index=date_index, columns=['Predicted Close'])
actual_prices = aapl['Close'][train_size+60:train_size+60+len(predicted_prices)]

# Define MSE calculation function
def calculate_mse(predicted, actual):
    mse = mean_squared_error(actual, predicted)
    print(f"Mean Squared Error: {mse}")

calculate_mse(predicted_prices.flatten(), actual_prices.values)

# Plotting the results
plt.figure(figsize=(15, 5))
plt.plot(actual_prices.index, actual_prices.values, color='red', label='Real AAPL Stock Price')
plt.plot(predicted_prices_df.index, predicted_prices_df['Predicted Close'], color='blue', label='Predicted AAPL Stock Price')
plt.title('AAPL Stock Price Prediction')
plt.xlabel('Time')
plt.ylabel('AAPL Stock Price')
plt.legend()
plt.show()



