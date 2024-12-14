import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import math
import yfinance as yf
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error
from keras.models import Sequential
from keras.layers import Dense, Activation, LSTM, Dropout
from keras import preprocessing
import matplotlib.dates as mdates
from pandas_datareader import data as pdr
from pandas_datareader.data import DataReader
import seaborn as sns

from datetime import datetime


#import stock data from yahoo finance
aapl = yf.Ticker("aapl")
aapl_prices = aapl.history(start="2022-01-01", period = 'max', interval="1h")

tsla = yf.Ticker("tsla")
tsla_prices = tsla.history(start="2022-01-01", period = 'max', interval="1h")

nvda = yf.Ticker("nvda")
nvda_prices = nvda.history(start="2022-01-01", period = 'max', interval="1h")

yf.pdr_override()

#Prepare data for easier visualization

tech_list = ["aapl", "tsla", "nvda"]

end = datetime.now()
start = datetime(end.year - 1, end.month, end.day)

for stock in tech_list:
    globals()[stock] = yf.download(stock, start, end)

company_list = [aapl, tsla, nvda]
company_name = ["aapl", "tsla", "nvda"]

for company, com_name in zip(company_list, company_name):
    company["company_name"] = com_name

df = pd.concat(company_list, axis=0)
# Let's see a historical view of the closing price
plt.figure(figsize=(15, 10))
plt.subplots_adjust(top=1.25, bottom=1.2)

for i, company in enumerate(company_list, 1):
    plt.subplot(2, 2, i)
    company['Adj Close'].plot()
    plt.ylabel('Adj Close')
    plt.xlabel(None)
    plt.title(f"Closing Price of {tech_list[i - 1]}")

plt.tight_layout()


# Visualize the trading volume for each stock
plt.figure(figsize=(15, 10))
plt.subplots_adjust(top=1.25, bottom=1.2)

for i, company in enumerate(company_list, 1):
    plt.subplot(2, 2, i)
    company['Volume'].plot()
    plt.ylabel('Volume')
    plt.xlabel(None)
    plt.title(f"Sales Volume for {tech_list[i - 1]}")

plt.tight_layout()

# Feature sclaing. Close price is used as the feature in time series
close_val = aapl_prices['Close'].values
close_val_t = np.reshape(close_val, (len(close_val),1))
scaler = MinMaxScaler(feature_range=(0, 1))
training_scaled = scaler.fit_transform(close_val_t)

x_train = []
y_train = []
for iter in range(60, 3000):
    x_train.append(training_scaled[iter-60:iter, 0])
    y_train.append(training_scaled[iter, 0])
x_train, y_train=np.array(x_train), np.array(y_train)
x_train = np.reshape(x_train, (x_train.shape[0], x_train.shape[1], 1))
step_size = 1

jeff_LSTM = Sequential()
jeff_LSTM.add(LSTM(units = 50, return_sequences = True, input_shape = (x_train.shape[1], 1)))
jeff_LSTM.add(Dropout(0.2))
jeff_LSTM.add(LSTM(units = 50, return_sequences = True))
jeff_LSTM.add(Dropout(0.2))
jeff_LSTM.add(LSTM(units = 50, return_sequences = True))
jeff_LSTM.add(Dropout(0.2))
jeff_LSTM.add(LSTM(units = 50))
jeff_LSTM.add(Dropout(0.2))
jeff_LSTM.add(Dense(units = 1))


jeff_LSTM.compile(optimizer = 'adam', loss = 'mean_squared_error')
jeff_LSTM.fit(x_train, y_train, epochs = 100, batch_size = 32)

data_train = aapl_prices.iloc[:3000, 3]
data_test = aapl_prices.iloc[:, 3]
data_total = pd.concat((data_train, data_test), axis = 0)
total_input = data_total[len(data_total) - len(data_test) - 1:].values
total_input = total_input.reshape(-1,1)
total_input = scaler.transform(total_input)
x_test = []
for iter in range(3000, len(data_test)):
    x_test.append(total_input[iter-60:iter, 0])
x_test = np.array(x_test)
x_test = np.reshape(x_test, (x_test.shape[0], x_test.shape[1], 1))
print(x_test.shape)

predicted_price = jeff_LSTM.predict(x_test)
predicted_price = scaler.inverse_transform(predicted_price)

#Reformat the data for MSE calculation
date_index = aapl_prices.index[3000:len(data_test)]
predicted_price = pd.DataFrame(predicted_price)
predicted_price.set_index(date_index, inplace=True)

from sklearn.metrics import mean_squared_error

#Define MSE generation function to generate MSE for hourly predicted MSE on given date
def calculate_hourly_mse(date, predicted_prices, actual_prices):
    # Filter the predicted and actual prices for the specified date
    predicted_prices_date = predicted_prices.loc[date]
    actual_prices_date = actual_prices.loc[date]

    # Calculate the MSE for each hour and print the results
    for hour in predicted_prices_date.index:
        try:
            mse = mean_squared_error([actual_prices_date.loc[hour]], [predicted_prices_date.loc[hour]])
            print(f"Date: {date}, Hour: {hour}, MSE: {mse}")
        except KeyError:
            print(f"No data available for hour: {hour}")

#We take a previous date to calculate the MSE to examine the perfomance of our model
date = "2023-11-09"
expected_value = data_test[3000:len(data_test)]
hourly_mse = calculate_hourly_mse(date, predicted_price, expected_value)
print(hourly_mse)

plt.plot(data_test, color = 'red', label = 'Real AAPL Stock Price')
plt.plot(predicted_price, color = 'blue', label = 'Predicted AAPL Stock Price')
plt.title('AAPL Stock Price Prediction')
plt.xlabel('Time')
plt.ylabel('AAPL Stock Price')
plt.legend()
plt.show()
