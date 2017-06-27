#!/bin/bash
source /home/ubuntu/.bash_aliases && source /home/ubuntu/anaconda3/bin/activate /home/ubuntu/anaconda3/envs/roto && python /home/ubuntu/roto-ranks/roto_ranks.py
aws s3 cp /home/ubuntu/roto-ranks/index/index.html s3://jgdwyer.com/roto-ranks/
aws s3 cp /home/ubuntu/roto-ranks/csv/roto_ranks.csv s3://jgdwyer.com/roto-ranks/data/
aws s3 cp /home/ubuntu/roto-ranks/csv/roto_stats.csv s3://jgdwyer.com/roto-ranks/data/
aws s3 cp /home/ubuntu/roto-ranks/figs/roto_ranks_bar_chart.png s3://jgdwyer.com/roto-ranks/figs/
aws s3 cp /home/ubuntu/roto-ranks/figs/timeseries.png s3://jgdwyer.com/roto-ranks/figs/
