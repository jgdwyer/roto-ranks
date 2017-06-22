#!/bin/bash
source /home/ubuntu/.bash_aliases && source /home/ubuntu/anaconda3/bin/activate /home/ubuntu/anaconda3/envs/roto && python /home/ubuntu/roto-ranks/roto_ranks.py
aws s3 cp index.html s3://jgdwyer.com/roto-ranks/
aws s3 cp roto_ranks.csv s3://jgdwyer.com/roto-ranks/data/

