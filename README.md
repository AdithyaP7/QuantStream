# QuantStream

**QuantStream** is a real-time stock market analytics system that empowers everyday traders by delivering advanced insights through enhanced data streaming, processing, storage, and analytics. This system integrates Kafka, Snowflake, and ThetaData API to create a robust, scalable, and interactive trading experience.

---

## Table of Contents
- [Features](#features)
- [Setup Instructions](#setup-instructions)
  - [1. Virtual Environment Setup](#1-virtual-environment-setup)
  - [2. Environment Variables](#2-environment-variables)
- [Data Streaming Setup](#data-streaming-setup)
  - [1. Open a ThetaTerminal](#1-open-a-thetaterminal)
  - [2. Start Zookeeper & Kafka](#2-start-zookeeper--kafka)
  - [3. Start Kafka Consumer](#3-start-kafka-consumer)
  - [4. Start Kafka Producer](#4-start-kafka-producer)
  - [5. Kafka Snowflake Sink Connector](#5-kafka-snowflake-sink-connector)
  - [6. Snowflake Database Setup](#6-snowflake-database-setup)
  - [7. Snowflake Python Worksheet](#7-snowflake-python-worksheet)
- [Machine Learning Setup](#machine-learning-setup)
  - [1. Machine Learning + Flask Application](#1-machine-learning--flask-application)
- [Notes](#notes)
- [License](#license)

---

## Features
- Real-time stock data streaming using **Kafka**.
- Historical and live data fetching via **Alpha Vantage API**.
- Seamless data storage and processing using **Snowflake**.
- Modular and extensible architecture for enhanced trading analytics.
  
---

## Setup Instructions

### 1. Virtual Environment Setup
First, set up a virtual environment to manage dependencies:

```bash
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Environment Variables
Create a `.env` file in the project root directory and populate it with your credentials:

```
SNOWFLAKE_USER=your_snowflake_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_ACCOUNT=your_account_identifier
```

---

## Data Streaming Setup

### 1. Open a ThetaTerminal
QuantStream uses the **ThetaData API** for real-time and historical stock data.

Run this command to start the terminal:
```bash
java -jar ThetaTerminal.jar quantstream.09@gmail.com Quantstream123
```

### 2. Start Zookeeper & Kafka

Navigate to your Kafka directory:

```bash
cd kafka_2.13-3.9.0
```

Open **three new separate terminals** and execute the following:

- **Terminal 1: Start Zookeeper Server**
  ```bash
  bin/zookeeper-server-start.sh config/zookeeper.properties
  ```

- **Terminal 2: Start Kafka Server**
  ```bash
  bin/kafka-server-start.sh config/server.properties
  ```

- **Terminal 3: Create Kafka Topic**
  ```bash
  bin/kafka-topics.sh --create --topic stock_data --bootstrap-server localhost:9091 --replication-factor 1 --partitions 1
  ```

### 3. Start Kafka Consumer
Monitor stock data flow using:

```bash
bin/kafka-console-consumer.sh --topic stock_data --from-beginning --bootstrap-server localhost:9091
```

### 4. Start Kafka Producer
Poll data from the ThetaData API and publish JSON message to the stock_data Kafka topic:
```bash
python newdata.py
```


### 5. Kafka Snowflake Sink Connector

- Update the Kafka Connect standalone properties file (different path depending on your file tree):
  ```properties
  plugin.path=/Users/akshaymistry/Dev/gt/cs4440/QuantStream/kafka_2.13-3.9.0/libs
  ```

- Ensure Kafka uses the correct Java architecture:

  ```bash
  export JAVA_HOME=$(/usr/libexec/java_home -v 17 --arch x86_64)
  ```

- Run the Snowflake Connector:

  ```bash
  cd kafka_2.13-3.9.0 
  arch -x86_64 ./bin/connect-standalone.sh \
      config/connect-standalone.properties \
      config/SF_connect.properties
  ```

Suggested Terminal setup at this point:
![image](https://github.com/user-attachments/assets/bd037e87-65f9-4394-be75-e914a593accc)


### 6. Snowflake Database  
Configured in **“Schema Setup” SQL Worksheet**

QuantStream streams raw Kafka messages into Snowflake for long-term storage and structured querying.

**Streaming flow**

1. Kafka topic **`stock_data`** → Snowflake Sink Connector (flush every 30 s).  
2. Records land in **`STOCK_DB.STOCK_SCHEMA.TEST_CONNECTOR`** with two `VARIANT` columns:  
   - **`RECORD_METADATA`** – Kafka metadata (partition, offset, timestamp).  
   - **`RECORD_CONTENT`** – JSON payload containing stock data.

**Example raw row**

| RECORD_METADATA | RECORD_CONTENT |
|-----------------|----------------|
| `{ "CreateTime": 1745633577560, "offset": 380, "partition": 0, "topic": "stock_data" }` | `{ "stock_symbol": "MSFT", "timestamp_utc": "2025-04-26T02:12:57.000Z", "open_price": 387, "close_price": 391.85, "current_price": 392.2, "volume": 15023161 }` |

---

#### Schema Setup (SQL)

```sql
-- 1) Database & schema
CREATE OR REPLACE DATABASE STOCK_DB;
CREATE OR REPLACE SCHEMA  STOCK_DB.STOCK_SCHEMA;

-- 2) Kafka landing table (raw JSON)
CREATE OR REPLACE TABLE STOCK_DB.STOCK_SCHEMA.TEST_CONNECTOR (
    RECORD_METADATA VARIANT,
    RECORD_CONTENT  VARIANT
);
```

### 7. Snowflake Python Worksheet  
Configured in **“ML Models” Python Worksheet**

The worksheet uses **Snowpark for Python** to unpack JSON stored in `STOCK_DB.STOCK_SCHEMA.TEST_CONNECTOR` and return a clean DataFrame for analytics and machine-learning workloads.

**Workflow**

1. **Query** the landing table and extract fields from `RECORD_CONTENT`.  
2. **Cast** each JSON value to the proper data type (STRING, FLOAT, etc.).  
3. **Filter / order** as needed (example below restricts to the symbol `AAPL`).  
4. **Return** a Snowpark DataFrame that downstream code can convert to Pandas or feed directly into ML pipelines.

```python
import snowflake.snowpark as snowpark

def main(session: snowpark.Session):
    df = session.sql("""
        SELECT
            RECORD_CONTENT:stock_symbol::STRING  AS stock_symbol,
            RECORD_CONTENT:timestamp_utc::STRING AS timestamp_utc,
            RECORD_CONTENT:open_price::FLOAT     AS open_price,
            RECORD_CONTENT:close_price::FLOAT    AS close_price,
            RECORD_CONTENT:current_price::FLOAT  AS current_price
        FROM STOCK_DB.STOCK_SCHEMA.TEST_CONNECTOR
        WHERE RECORD_CONTENT:stock_symbol::STRING = 'AAPL'
        ORDER BY timestamp_utc
    """)
    return df  # Snowpark DataFrame ready for ML or Pandas
```

---

## Machine Learning Setup

### 1. Machine Learning + Flask Application
Configured in "ML Models" Python Worksheet

1. **Packages** Install all necessary packages via `requirements.txt`.
2. **Start Flask App** Start flask app by running `python app.py` in python-scripts directory
3. **View** forecasts, historical data, and current time dashboards on interactive flask app in web browser.

Long Short-Term Memory (LSTM) models are a type of recurrent neural network (RNN) specialized for learning long-term dependencies in sequential data, making them well-suited for forecasting stock prices based on patterns in historical returns. LSTM models can be tuned by adjusting the number of layers, hidden units, window size, learning rate, batch size, and number of training epochs to better capture underlying patterns in the stock data.

Prophet, developed by Facebook, is an additive time series forecasting model designed to handle seasonality, holidays, and trend shifts with minimal parameter tuning, offering fast, interpretable predictions for business and financial data. Prophet models can be tuned by modifying changepoint sensitivity, seasonality modes (additive or multiplicative), and manually adding known holidays or events to improve forecast accuracy around significant disruptions.


---

## Notes
- Ensure all Kafka and Zookeeper services are properly configured with open ports.
- For best performance, use **Java 17** with **x86_64** architecture when running Kafka Connect.
- Data privacy and security are paramount. Keep your `.env` file out of version control.

---
