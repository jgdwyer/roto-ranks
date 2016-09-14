# roto-ranks
Calculates the rotisserie rankings for CBS Sports fantasy baseball leagues

For fantasy baseball head-to-head leagues on CBS Sports there is no way to calculate rotosserie rankings. (In this system each team is ranked from first to last in each scoring statistic. The rankings are then tallied to give an overall score). This code makes this calculation by downloading the html page of team statistics for the user's league, scraping the html page, and then calculating the rankings.

I used the following packages: numpy, pandas, beautifulsoup, matplotlib, requests. Code was written for python3.

These choices were more motivated by my interest in learning to use these packages than by writing code which would not require much set up.

![Sample output](sample/sample_ranks.png)
