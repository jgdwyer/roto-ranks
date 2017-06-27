import roto_scripts as r

# Access html page of team stats from web
html = r.download_html()

# Scrape html page and store stats as a pandas data frame object
stats = r.scrape_html(html)

# Calculate roto rankings 
ranks = r.calculate_ranks(stats)

# Update html file to reflect new day's stats
r.updateIndexHTML()

# Make bar chart
r.plot_ranks_bar(ranks)

# Make time series and update history csv
r.updateHistory(ranks)
