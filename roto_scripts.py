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

def download_html():
    """Returns html file corresponding to year-to-date team scoring stats page"""
    # Prompt user for league name, user name, and password
    user, password, league, _ = loadCredentials()
    # Desired html page
    myurl = 'http://' + league + '.baseball.cbssports.com/stats/' + \
             'stats-main/teamtotals/ytd:f/scoring/stats'
    # Authenticating page
    loginurl = 'https://auth.cbssports.com/login/index'
    # Procedure from: https://brennan.io/2016/03/02/logging-in-with-requests/
    s = requests.session()
    login = s.get(loginurl)
    # Get the post data
    login_html = lxml.html.fromstring(login.text)
    hidden_inputs = login_html.xpath(r'//form//input[@type="hidden"]')
    form = {x.attrib["name"]: x.attrib["value"] for x in hidden_inputs}
    form['userid'] = user
    form['password'] =password
    response = s.post(loginurl, data=form)
    r = s.get(myurl)
    return r.content

def loadCredentials():
    user = os.environ['JABOUSER']
    password = os.environ['JABOPASS']
    league = os.environ['JABOLEAGUE']
    N_teams = os.environ['JABOTEAMS']
    return user, password, league, N_teams

def askCredentials():
    user   = input('Enter user name: ')
    print('Enter password')
    password = getpass.getpass()
    league = input('Enter short league name (e.g., jabo for jabo.baseball.cbssports.com): ')
    N_teams = input('Enter the number of teams in the league: ')
    return user, password, league, N_teams

def scrape_html(html):
    """Scrapes cbssports html page and returns a pandas dataframe of sorted team
    totals using the beautiful soup package"""
    # Use the beautiful soup package to parse html file
    soup = BeautifulSoup(html,'lxml')
    # This gets all of the relevant team stats and none of the unnecessary html junk
    rows = soup.find_all('tr')
    # To do: update below to automatically calculate number of teams in the league
    _, _, _, N_teams = loadCredentials()
    N_teams = int(N_teams)
    # Initialize data for table
    H_count = 0
    P_count = 0
    H_teams = []
    P_teams = []
    H_headers = []
    P_headers = []
    H_stats = np.zeros((N_teams, 8))
    P_stats = np.zeros((N_teams, 8))
    # These values say where the hitting and pitching headers begin
    H_offset = 3
    P_offset = 2 * H_offset + 1 + N_teams
    # Loop through rows to get the player infoa
    for row_count, row in enumerate(rows):
        # Header for hitting stats
        if row_count == H_offset:
            H_headers = [entry.string for entry in row.contents]
        # Header for pitching stats
        if row_count == P_offset:
            P_headers = [entry.string for entry in row.contents]
        # Values for hitting stats
        if (row_count > H_offset and row_count <= H_offset + N_teams):
            H_teams.append(row.contents.pop(0).string)
            H_stats[H_count, :] = [float(val.string) for val in row.contents]
            H_count += 1
        # Values for pitching stats
        if (row_count > P_offset and row_count <= P_offset + N_teams):
            P_teams.append(row.contents.pop(0).string)
            P_stats[P_count, :] = [float(val.string) for val in row.contents]
            P_count += 1
    # Remove the "team" entry from the headers file
    H_headers.pop(0)
    P_headers.pop(0)
    # Convert to pandas data frame and combine hitting and pitching stats
    h = pd.DataFrame(H_stats, index=H_teams, columns=H_headers)
    p = pd.DataFrame(P_stats, index=P_teams, columns=P_headers)
    stats = pd.concat([h, p], axis=1)
    return stats

def calculate_ranks(stats):
    """Create a new pandas data frame for the relative ranks of each team in each
    category (e.g., team with least HR gets 1 point, team with 2nd least HR gets
    2 points, etc.) In the case of a tie in a category, teams split the points
    This ensures that all categories have the same number of total points awarded
    Warning: BA, OBP, SLG, ERA, etc. can be taken out to more decimal places..
    This could be important for breaking ties (To Do!)"""
    N_teams = len(stats)
    ranks=stats.rank(axis=0, method='average')
    # For some categories, the smallest values are best. Account for this here:
    ascending = ['ERA', 'WHIP']
    for cat in ascending:
        ranks[cat] = N_teams + 1 - ranks[cat]
    # Sum up each team's points to get their total roto ranking
    scores = ranks.sum(axis=1).sort_values()
    # Add the ranks field to our ranks data frame
    ranks['scores'] = scores
    # Reorder columns
    ranks = ranks[['BA', 'OBP', 'R', 'SB', 'RBI', 'HR', 'TB', 'SLG',
                   'ERA', 'WHIP', 'INNdGS', 'W', 'K', 'K/BB', 'HD', 'S', 'scores']]
    # Sort by team with best overall roto ranking
    ranks = ranks.sort_values('scores', ascending=False)
    # Save the ranks as a csv file too
    ranks.to_csv('./csv/roto_ranks_' + time.strftime("%Y-%m-%d") + '.csv')
    ranks.to_csv('./csv/roto_ranks.csv')
    return ranks

def updateIndexHTML(indexfile):
    # Read in the file
    with open(indexfile, 'r') as f:
        filedata = f.read()
    # Replace the target string
    filedata = filedata.replace('Statistics Updated on ',
                                'Statistics Updated on ' + time.strftime("%Y-%m-%d"))
    # Write the file out again
    with open('./index/index.html', 'w') as f:
        f.write(filedata)


def formatRanksDateTime(ranks):
    """Takes a ranks data frame, Extracts scores and returns a one-row dataframe
    with team names as columns and datetime as index (pivot)"""
    z = z['scores']
    z = z.to_frame()
    z = z.transpose()
    z = z.set_index(pd.DatetimeIndex([time.strftime("%Y-%m-%d")]))

def mergeSaveSeasonHistory(ranks, ranks_all_filename):
    """Loads the ranks_all_filename dataframe and adds a new row to it"""
    ranks_all = pd.read_csv(ranks_all_filename, index_col=[0], parse_dates=[0])
    ranks_all = pd.concat([ranks_all, ranks], axis=0)
    ranks_all.to_csv('./history/' + ranks_all_filename + '_' +
                     time.strftime("%Y-%m-%d") + '.csv')
    ranks_all.to_csv(ranks_all_filename + '.csv')
    return ranks_all

def plot_ranks_bar(ranks):
    """Makes a stacked bar chart of ranks"""
    # Drop score category for plotting
    ranks = ranks.drop('scores', axis=1)
    cmap = def_colormap()
    matplotlib.style.use('ggplot')
    ranks.plot.barh(stacked=True, colormap=cmap, figsize=(8, 6))
    plt.gca().legend(loc='center left', bbox_to_anchor=(1, 0.5))
    plt.savefig('./roto_ranks_bar_chart_' + time.strftime("%Y-%m-%d") + '.pdf',
                bbox_inches='tight')
    # To do: add a datestamp to filenames

def def_colormap():
    """Returns a colormap that separates hitting and pitching categories"""
    # 8 hitting categories and 8 pitching categories
    colors1 = plt.cm.Reds(np.linspace(0, 1, 8))
    colors2 = plt.cm.Blues(np.linspace(0, 1, 8))
    # combine them and build a new colormap
    colors = np.vstack((colors1, colors2))
    mymap = mcolors.LinearSegmentedColormap.from_list('my_colormap', colors)
    return mymap
