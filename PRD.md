# Fatcules: python telegram bot for tracking weight and fat changes

This telegram bot is used for getting the User's weight and fat, and getting statistics on a progress. This bot is created in Python, using aiogram library. It should use a lightweight database to store the values. 

Features:
- Virtual keyboard with buttons 
    - Add a new entry with weight and optionnally the fat percentage
    - Edit an entry (with numbered list to select which entry to edit) 
    - Remove an entry (with numbered list to select which entry to delete)
    - Get the statistics
- Statistics button returns a picture 
    - With the fat weight (total weight * fat percentage)
    - With an average drop in the fat weight during last 7, 14 and 30 days.
    - It also shows a graph of fat-weight over time

