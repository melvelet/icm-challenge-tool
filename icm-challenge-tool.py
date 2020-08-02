import csv
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


class IcmChallengeTool:
    def __init__(self, challenge_list):
        self.challenge_list = challenge_list
        self.users = self.__create_users_dict()
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
                    'checks_counts': list(),
                    'imdb_ids': list()
                }
            users[user]['count'] += 1
            users[user]['checks_counts'].append(entry[CHECKS])
            imdb = [content for content in entry[IMDB].split('/') if content.startswith('tt')]
            if imdb:
                users[user]['imdb_ids'].append(imdb[0])

        return users

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
        leaderboard = '[table]\n[tr][td][b]	Rank	[/b][/td][td][b]	Participant	[/b][/td][td][b]	Count	[/b]\
        [/td][td][b]	Count (500<400)	[/b][/td][td][b]	Count (501-1000<400)	[/b][/td][td][b]	Count \
        (non-500<400)	[/b][/td][/tr]\n'
        last_count = 100000
        last_i = 0
        for i, (username, count) in enumerate(leader_list):
            leaderboard += f"[tr][td]	{last_i if count == last_count else i + 1}	[/td][td]	{username}	[/td]"
            leaderboard += f"[td]	{count}	[/td][td]	{self.get_count_of_entries_in_500(username)}	[/td]"
            leaderboard += f"[td]	{self.get_count_of_entries_in_1000(username)}	[/td]"
            leaderboard += f"[td]	{self.get_count_of_entries_not_in_top_list(username)}	[/td][/tr]\n"
            if last_count > count:
                last_i = i + 1
                last_count = count
        leaderboard += '[/table]'
        print(leaderboard)



if __name__ == '__main__':
    challenge_list = open_csv('lessthan400.csv', ';')
    ct = IcmChallengeTool(challenge_list)
    # print(ct.create_users_dict().sort(key='count'))
    ct.print_leaderboard()
