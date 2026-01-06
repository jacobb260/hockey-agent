## Introduction

This project is an NHL-focused hockey agent designed to help users learn more about the National Hockey League. The agent allows users to ask questions about players, teams, and goaltenders, and to compare them using statistics such as points, goals, and save percentage. It is intended as an educational tool that makes NHL data easier to explore and understand. Here's a link to the agent:
https://huggingface.co/spaces/plays1/hockey-agent 

## Data Source and Storage

The agent retrieves its data from the NHL API, which provides up-to-date and detailed hockey statistics. The data is updated daily and the agent has access to data from 2000 onward. More information about the API can be found here:
https://github.com/Zmalski/NHL-API-Reference

For data storage, Hopsworks is used to manage and persist the collected information efficiently.

## LLM Model

The agent is powered by the Gemma 3 27B large language model, which enables natural language interaction and helps transform raw NHL data into clear and meaningful answers for users.

## Functionalities

The agent has access to several built-in tools that extend its capabilities. These tools allow it to:

Retrieve player overviews and statistics

Identify and compare top-performing players

Provide team overviews

Fetch information about specific games

Analyze and assess goaltender performance

All results are presented in markdown-formatted tables, giving users a clear and structured overview that makes comparisons and statistics easy to read and understand.

## Setup

This project uses Conda for environment management.

### Create Conda environment

```bash
conda env create -f environment.yml
conda activate hockey-agent
```

### Environment variables

Set the following environment variables:

```text
GOOGLE_API_KEY=your_google_api_key
HOPSWORKS_API_KEY=your_hopsworks_api_key
HOPSWORKS_PROJECT=your_hopsworks_project
HOPSWORKS_HOST=your_hopsworks_host
```

These can be set in a `.env` file or exported in your shell.

## Run the agent locally

To run the agent locally on your own computer:

```bash
cd hockey-agent/agent
python agentApp.py
```

The UI can be accessed at:

```
http://localhost:7860/
```

