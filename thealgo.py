"""
A script to simulate random updating of posts in a website.
"""

#! python3
# thealgo.py - An algorithm to rank posts

# Import modules
import time, datetime
import random
import os, json


# Create a dictionary of posts
posts = ['post 1', 'post 2', 'post 3', 'post 4', 'post 5', 'post 6', 'post 7']

# Original ranking with 0 score for each post
rank = {'post 1':0, 'post 2':0, 'post 3':0, 'post 4':0, 'post 5':0, 'post 6':0, 'post 7':0}

# Create a json file
with open('rank.txt', 'w') as outfile:
    json.dump(rank, outfile)


# Loop to bring up the post in question
while True:
    # load json file of posts
    with open('rank.txt') as json_file:
        data = json.load(json_file)
    select = random.randint(0, 6)
    # Prompt for user input
    vote_c = input("What do you vote for %s" % (posts[select]))
    post_num = list(list(data.items())[select])[0]
    # Edit the dictionary on new score
    rank[post_num] = rank[post_num] + int(vote_c)
    timestamp = datetime.datetime.now()
    # Write new json file
    with open('rank.txt', 'w') as outfile:
     json.dump(rank, outfile)
    print(timestamp)
    
    # sort dictionary from most popular
    sorted_rank = sorted(data.items(), key=lambda x: x[1], reverse=True)
    print(sorted_rank)
    time.sleep(random.randint(2,30))

    

