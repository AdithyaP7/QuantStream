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


### 6. Snowflake Database Setup
Configured in "Schema Setup" SQL Worksheet

TO-DO

### 7. Snowflake Python Worksheet
Configured in "ML Models" Python Worksheet

TO-DO

---

## Machine Learning Setup

### 1. Machine Learning + Flask Application
Configured in "ML Models" Python Worksheet

TO-DO

---

## Notes
- Ensure all Kafka and Zookeeper services are properly configured with open ports.
- For best performance, use **Java 17** with **x86_64** architecture when running Kafka Connect.
- Data privacy and security are paramount. Keep your `.env` file out of version control.

---
