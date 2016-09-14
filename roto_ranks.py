import roto_scripts as r

# Access html page of team stats from web
html = r.download_html()

# Scrape html page and store stats as a pandas data frame object
stats = r.scrape_html(html)

# Calculate roto rankings 
ranks = r.calculate_ranks(stats)
