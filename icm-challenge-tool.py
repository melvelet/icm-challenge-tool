import csv, yaml
import statistics
import subprocess
from collections import Counter

USER = 0
IMDB = 1
CHECKS = 2
YEAR = 3
COUNTRY = 4


def open_csv(file, delimiter):
    result = list()
    with open(file, encoding='latin-1') as csvfile:
        for entry in csv.reader(csvfile, delimiter=delimiter):
            result.append(entry)
    return result[1:]


def open_yaml(filename):
    with open(f"{filename}.yaml") as file:
        return yaml.load(file, Loader=yaml.FullLoader)


def write_to_clipboard_mac(output):
    process = subprocess.Popen(
        'pbcopy', env={'LANG': 'en_US.UTF-8'}, stdin=subprocess.PIPE)
    process.communicate(output.encode('utf-8'))


class IcmChallengeTool:
    def __init__(self, challenge_list):
        self.challenge_list = challenge_list
        self.users = self.__create_users_dict()
        self.__map_nominations_to_users()
        self.fivehundred, self.thousand = self.__get_500_list()

    def __get_500_list(self):
        lst = open_csv('1000.csv', ',')
        fivehundred = list()
        thousand = list()
        for rank, entry in enumerate(lst):
            imdb = [content for content in entry[11].split('/') if content.startswith('tt')][0]
            if rank < 500:
                fivehundred.append(imdb)
            else:
                thousand.append(imdb)

        return fivehundred, thousand

    def __create_users_dict(self):
        users = dict()
        for entry in self.challenge_list:
            user = entry[USER]
            if user not in users:
                users[user] = {
                    'count': 0,
                    'check_counts': list(),
                    'imdb_ids': list()
                }
            users[user]['count'] += 1
            if entry[CHECKS]:
                users[user]['check_counts'].append(int(entry[CHECKS]))
            imdb_url = [content for content in entry[IMDB].split('/') if content.startswith('tt')]
            if imdb_url:
                users[user]['imdb_ids'].append(imdb_url[0])

        return users

    def __map_nominations_to_users(self):
        mappings = open_yaml('nominations')
        for username, val in self.users.items():
            self.users[username]['nomination'] = mappings[username]['link'] if username in mappings else None

    def get_leader_list(self):
        def take_second(elem):
            return elem[1]

        user_count_list = [(user_name, user['count']) for user_name, user in self.users.items()]
        return sorted(user_count_list, key=take_second, reverse=True)

    def get_count_of_entries_in_500(self, username):
        imdbs = [imdb for imdb in self.users[username]['imdb_ids'] if imdb in self.fivehundred]
        return len(imdbs)

    def get_count_of_entries_in_1000(self, username):
        imdbs = [imdb for imdb in self.users[username]['imdb_ids'] if imdb in self.thousand]
        return len(imdbs)

    def get_count_of_entries_not_in_top_list(self, username):
        imdbs = [imdb for imdb in self.users[username]['imdb_ids'] if imdb not in self.thousand + self.fivehundred]
        return len(imdbs)

    def print_leaderboard(self):
        leader_list = self.get_leader_list()
        leaderboard = f"[table]\n[tr][td][b]\tRank\t[/b][/td][td][b]\tParticipant\t[/b][/td][td][b]\tCount\t[/b][/td]" \
                      f"[td][b]Check count: Mean / Median[/b][/td]" \
                      f"[td][b]500<400	/ 501-1000 / neither[/b][/td]" \
                      f"[td][b]1>500<400[/b][/td]" \
                      f"[/tr]\n"
        last_count = 100000
        last_i = 0
        for i, (username, count) in enumerate(leader_list):
            leaderboard += f"[tr][td]\t{last_i if count == last_count else i + 1}\t[/td]" \
                           f"[td]\t{username}\t[/td]" \
                           f"[td]\t{count}\t[/td]"
            leaderboard += self.__get_check_stats_cell(username)
            leaderboard += self.__get_500_400_cell(username)
            leaderboard += self.__get_nomination_cell(username)
            leaderboard += f"[/tr]\n"
            if last_count > count:
                last_i = i + 1
                last_count = count
        leaderboard += '[/table]'
        return leaderboard

    def __get_nomination_cell(self, username):
        if self.users[username]['nomination']:
            return f"[td]   [url={self.users[username]['nomination']}] :ICM: [/url] [/td]"
        else:
            return f"[td]   -   [/td]"

    def __get_500_400_cell(self, username):
        return f"[td]	{self.get_count_of_entries_in_500(username)} / " \
               f"{self.get_count_of_entries_in_1000(username)} / " \
               f"{self.get_count_of_entries_not_in_top_list(username)}  [/td]"

    def __get_check_stats_cell(self, username):
        return f"[td]\t{self.get_check_count_mean(username):.1f} / {self.get_check_count_median(username):.1f}\t[/td]"

    def get_check_count_mean(self, username):
        return statistics.mean(self.users[username]['check_counts'])

    def get_check_count_median(self, username):
        return statistics.median(self.users[username]['check_counts'])


if __name__ == '__main__':
    challenge_list = open_csv('lessthan400.csv', ';')
    ct = IcmChallengeTool(challenge_list)
    # print(ct.create_users_dict().sort(key='count'))
    table = ct.print_leaderboard()
    print(table)
    write_to_clipboard_mac(table)
