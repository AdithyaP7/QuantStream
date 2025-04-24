# QuantStream

**QuantStream** is a real-time stock market analytics system that empowers everyday traders by delivering advanced insights through enhanced data streaming, processing, storage, and analytics. This system integrates Kafka, Snowflake, and Alpha Vantage API to create a robust, scalable, and interactive trading experience.

---

## Table of Contents
- [Features](#features)
- [Setup Instructions](#setup-instructions)
  - [1. Virtual Environment Setup](#1-virtual-environment-setup)
  - [2. Environment Variables](#2-environment-variables)
- [Kafka Setup](#kafka-setup)
  - [1. Start Zookeeper & Kafka](#1-start-zookeeper--kafka)
  - [2. Create Kafka Topic](#2-create-kafka-topic)
  - [3. Start Kafka Consumer](#3-start-kafka-consumer)
  - [4. Kafka Snowflake Sink Connector](#4-kafka-snowflake-sink-connector)
- [API Integration](#api-integration)
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
ALPHA_VANTAGE_API_KEY=5SIOLTZC95CTPAJF
SNOWFLAKE_USER=your_snowflake_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_ACCOUNT=your_account_identifier
```

---

## Kafka Setup

### 1. Start Zookeeper & Kafka

Navigate to your Kafka directory:

```bash
cd kafka_2.13-3.9.0
```

Open **three separate terminals** and execute the following:

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

### 2. Start Kafka Consumer
Monitor stock data flow using:

```bash
bin/kafka-console-consumer.sh --topic stock_data --from-beginning --bootstrap-server localhost:9091
```

---

### 3. Kafka Snowflake Sink Connector

- Update the Kafka Connect standalone properties file:
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

---

## API Integration
QuantStream uses the **Alpha Vantage API** for real-time and historical stock data.

- Sample API Key (for development/testing):
  ```
  5SIOLTZC95CTPAJF
  ```

Visit [Alpha Vantage](https://www.alphavantage.co/documentation/) for full API documentation.

---

## Notes
- Ensure all Kafka and Zookeeper services are properly configured with open ports.
- For best performance, use **Java 17** with **x86_64** architecture when running Kafka Connect.
- Data privacy and security are paramount. Keep your `.env` file out of version control.

---
