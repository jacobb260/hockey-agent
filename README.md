##Introduction

This project is an NHL-focused hockey agent designed to help users learn more about the National Hockey League. The agent allows users to ask questions about players, teams, and goaltenders, and to compare them using statistics such as points, goals, and save percentage. It is intended as an educational tool that makes NHL data easier to explore and understand.

##Data Source and Storage

The agent retrieves its data from the NHL API, which provides up-to-date and detailed hockey statistics. More information about the API can be found here:
https://github.com/Zmalski/NHL-API-Reference

For data storage, Hopsworks is used to manage and persist the collected information efficiently.

##LLM Model

The agent is powered by the Gemma 3 27B large language model, which enables natural language interaction and helps transform raw NHL data into clear and meaningful answers for users.

##Functionalities

The agent has access to several built-in tools that extend its capabilities. These tools allow it to:

Retrieve player overviews and statistics

Identify and compare top-performing players

Provide team overviews

Fetch information about specific games

Analyze and assess goaltender performance

All results are presented in markdown-formatted tables, giving users a clear and structured overview that makes comparisons and statistics easy to read and understand.
