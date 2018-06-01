import getpass
import lxml.html
import requests
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import boto3

rootpath = './'

s3 = boto3.resource('s3')
bucket_name = os.environ['ROTO_S3_BUCKET']


def download_html():
    """Returns html file corresponding to year-to-date team scoring stats page
    Procedure from: https://brennan.io/2016/03/02/logging-in-with-requests/"""
    # Prompt user for league name, user name, and password
    user, password, league, _ = loadCredentials()
    # Desired html page
    myurl = f'http://{league}.baseball.cbssports.com/stats/stats-main/teamtotals/ytd:f/scoring/stats'
    # Authenticating page
    loginurl = 'https://www.cbssports.com/login'
    s = requests.session()
    login = s.get(loginurl)
    # Get the post data
    login_html = lxml.html.fromstring(login.text)
    hidden_inputs = login_html.xpath(r'//form//input')
    form = {x.attrib["name"]: x.attrib["value"] for x in hidden_inputs if x.attrib['type'] != 'checkbox'}
    form['userid'] = user
    form['password'] = password
    _ = s.post(loginurl, data=form)
    r = s.get(myurl)
    return r.content


def loadCredentials():
    """Loads credentials from environmental variables"""
    user = os.environ['JABOUSER']
    password = os.environ['JABOPASS']
    league = os.environ['JABOLEAGUE']
    N_teams = os.environ['JABOTEAMS']
    return user, password, league, N_teams


def ask_credentials():
    """Manually asks user to enter credentials"""
    user = input('Enter user name: ')
    print('Enter password')
    password = getpass.getpass()
    league = input('Enter short league name (e.g., jabo for jabo.baseball.cbssports.com): ')
    n_teams = input('Enter the number of teams in the league: ')
    return user, password, league, n_teams


def scrape_html(html):
    """Scrapes cbssports html page and returns a pandas dataframe of sorted team
    totals using the beautiful soup package"""
    # Use the beautiful soup package to parse html file
    soup = BeautifulSoup(html, 'lxml')
    # This gets all of the relevant team stats and none of the unnecessary html junk
    rows = soup.find_all('tr')
    # To do: update below to automatically calculate number of teams in the league
    _, _, _, n_teams = loadCredentials()
    n_teams = int(n_teams)
    # Initialize data for table
    h_count = 0
    p_count = 0
    h_teams = []
    p_teams = []
    h_headers = []
    p_headers = []
    h_stats = np.zeros((n_teams, 8))
    p_stats = np.zeros((n_teams, 8))
    # These values say where the hitting and pitching headers begin
    h_offset = 3
    p_offset = 2 * h_offset + 1 + n_teams
    # Loop through rows to get the player infoa
    for row_count, row in enumerate(rows):
        # Header for hitting stats
        if row_count == h_offset:
            h_headers = [entry.string for entry in row.contents]
        # Header for pitching stats
        if row_count == p_offset:
            p_headers = [entry.string for entry in row.contents]
        # Values for hitting stats
        if h_offset < row_count <= h_offset + n_teams:
            h_teams.append(row.contents.pop(0).string)
            h_stats[h_count, :] = [float(val.string) for val in row.contents]
            h_count += 1
        # Values for pitching stats
        if p_offset < row_count <= p_offset + n_teams:
            p_teams.append(row.contents.pop(0).string)
            p_stats[p_count, :] = [float(val.string) for val in row.contents]
            p_count += 1
    # Remove the "team" entry from the headers file
    h_headers.pop(0)
    p_headers.pop(0)
    # Convert to pandas data frame and combine hitting and pitching stats
    h = pd.DataFrame(h_stats, index=h_teams, columns=h_headers)
    p = pd.DataFrame(p_stats, index=p_teams, columns=p_headers)
    stats = pd.concat([h, p], axis=1)
    return stats


def calculate_ranks(stats):
    """Create a new pandas data frame for the relative ranks of each team in each
    category (e.g., team with least HR gets 1 point, team with 2nd least HR gets
    2 points, etc.) In the case of a tie in a category, teams split the points
    This ensures that all categories have the same number of total points awarded
    Warning: BA, OBP, SLG, ERA, etc. can be taken out to more decimal places..
    This could be important for breaking ties (To Do!)"""
    n_teams = len(stats)
    ranks=stats.rank(axis=0, method='average')
    # For some categories, the smallest values are best. Account for this here:
    ascending = ['ERA', 'WHIP']
    for cat in ascending:
        ranks[cat] = n_teams + 1 - ranks[cat]
    # Sum up each team's points to get their total roto ranking
    scores = ranks.sum(axis=1).sort_values()
    # Add the ranks field to our ranks data frame
    ranks['scores'] = scores
    # Reorder columns
    ranks = ranks[['BA', 'OBP', 'R', 'SB', 'RBI', 'HR', 'TB', 'SLG',
                   'ERA', 'WHIP', 'INNdGS', 'W', 'K', 'K/BB', 'HD', 'S', 'scores']]
    stats = stats[['BA', 'OBP', 'R', 'SB', 'RBI', 'HR', 'TB', 'SLG',
                   'ERA', 'WHIP', 'INNdGS', 'W', 'K', 'K/BB', 'HD', 'S']]
    # Sort by team with best overall roto ranking
    ranks = ranks.sort_values('scores', ascending=False)
    # Save the ranks as a csv file too
    ranks.to_csv(rootpath + '/csv/roto_ranks_' + time.strftime("%Y-%m-%d") + '.csv')
    ranks.to_csv(rootpath + '/csv/roto_ranks.csv')
    for var in ['R', 'SB', 'RBI', 'HR', 'TB', 'W', 'K', 'HD', 'S']:
        stats[var] = stats[var].astype(int)
    stats.to_csv(rootpath + '/csv/roto_stats_' + time.strftime("%Y-%m-%d") + '.csv')
    stats.to_csv(rootpath + '/csv/roto_stats.csv')
    s3.Object(bucket_name, 'roto-ranks/data/roto_ranks.csv').upload_file(rootpath + '/csv/roto_ranks.csv')
    s3.Object(bucket_name, 'roto-ranks/data/roto_stats.csv').upload_file(rootpath + '/csv/roto_stats.csv')
    return ranks


def update_index_html():
    """Updates the index.html file to reflect that statistics have been updated for the current day"""
    # Read in the file
    indexfile = rootpath + '/index/index_orig.html'
    with open(indexfile, 'r') as f:
        filedata = f.read()
    # Replace the target string
    filedata = filedata.replace('Statistics updated on ',
                                'Statistics updated on ' + time.strftime("%Y-%m-%d"))
    # Write the file out again
    with open(rootpath + '/index/index.html', 'w') as f:
        f.write(filedata)
    s3.Object(bucket_name, 'roto-ranks/index.html').upload_file(rootpath + '/index/index.html')


def format_ranks_date_time(ranks):
    """Takes a ranks data frame, Extracts scores and returns a one-row dataframe
    with team names as columns and datetime as index (pivot)"""
    ranks = ranks['scores']
    ranks = ranks.to_frame()
    ranks = ranks.transpose()
    ranks = ranks.set_index(pd.DatetimeIndex([time.strftime("%Y-%m-%d")]))
    return ranks


def merge_save_season_history(ranks, ranks_all_filename):
    """Loads the ranks_all_filename dataframe and adds a new row to it"""
    try:
        ranks_all = pd.read_csv(ranks_all_filename, index_col=[0], parse_dates=[0])
    except FileNotFoundError:
        ranks_all = pd.DataFrame()
    if ranks.index[0] in ranks_all.index:
        print('Date already in this csv file. Not adding.')
    else:
        ranks_all = pd.concat([ranks_all, ranks], axis=0)
    ranks_all.to_csv(ranks_all_filename[:-4] + '_' +
                     time.strftime("%Y-%m-%d") + '.csv')
    ranks_all.to_csv(ranks_all_filename)
    return ranks_all


def update_history(ranks, ranks_date=None):
    """Updates the stats over time csv file and plots the time series graph"""
    out = format_ranks_date_time(ranks)
    if ranks_date is not None:
        out.index = pd.DatetimeIndex([ranks_date])
    merge_save_season_history(out, rootpath + '/csv/time_series.csv')
    plot_time_series(rootpath + '/csv/time_series.csv')


def plot_time_series(ranks_all_filename):
    """Plot time series of team rankings (assumes 14 teams)"""
    ranks_all = pd.read_csv(ranks_all_filename, index_col=[0], parse_dates=[0])
    matplotlib.style.use('ggplot')
    ranks_all.plot(colormap='gist_ncar',style=['-','--','-','--','-','--','-','--','-','--','-','--','-','--'])
    plt.gca().legend(loc='center left', bbox_to_anchor=(1, 0.5))
    plt.savefig(rootpath + '/figs/timeseries.png', bbox_inches='tight')
    plt.savefig(rootpath + '/figs/timeseries_' + time.strftime("%Y-%m-%d") + '.png', bbox_inches='tight')
    s3.Object(bucket_name, 'roto-ranks/figs/timeseries.png').upload_file(rootpath + '/figs/timeseries.png')


def plot_ranks_bar(ranks):
    """Makes a stacked bar chart of ranks"""
    # Drop score category for plotting
    ranks = ranks.drop('scores', axis=1)
    cmap = def_colormap()
    matplotlib.style.use('ggplot')
    ranks.plot.barh(stacked=True, colormap=cmap, figsize=(8, 6))
    plt.title('JABO Rotisserie Ranks through ' + time.strftime("%Y-%m-%d"))
    plt.gca().legend(loc='center left', bbox_to_anchor=(1, 0.5))
    plt.savefig(rootpath + '/figs/roto_ranks_bar_chart_' + time.strftime("%Y-%m-%d") + '.png',
                bbox_inches='tight')
    plt.savefig(rootpath + '/figs/roto_ranks_bar_chart.png', bbox_inches='tight')
    s3.Object(bucket_name, 'roto-ranks/figs/roto_ranks_bar_chart.png').upload_file(rootpath + '/figs/roto_ranks_bar_chart.png')


def def_colormap():
    """Returns a colormap that separates hitting and pitching categories"""
    # 8 hitting categories and 8 pitching categories
    colors1 = plt.cm.Reds(np.linspace(0, 1, 8))
    colors2 = plt.cm.Blues(np.linspace(0, 1, 8))
    # combine them and build a new colormap
    colors = np.vstack((colors1, colors2))
    mymap = mcolors.LinearSegmentedColormap.from_list('my_colormap', colors)
    return mymap
