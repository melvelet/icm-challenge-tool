import csv, yaml
import statistics
import requests
import subprocess
from collections import Counter


def open_csv(file, delimiter, encoding='utf-8'):
    result = list()
    with open(file, encoding=encoding) as csvfile:
        for entry in csv.reader(csvfile, delimiter=delimiter):
            result.append(entry)
    return result[0], result[1:]


def open_yaml(filename):
    with open(f"{filename}.yaml") as file:
        return yaml.load(file, Loader=yaml.FullLoader)


def write_to_clipboard_mac(output):
    process = subprocess.Popen(
        'pbcopy', env={'LANG': 'en_US.UTF-8'}, stdin=subprocess.PIPE)
    process.communicate(output.encode('utf-8'))
    print('Content copied to clipboard!')


def get_imdb_id_from_url(url):
    if not url:
        return None
    imdb_url = [content for content in url.split('/') if content.startswith('tt')]
    if imdb_url:
        return imdb_url[0]
    return None


class OMDBInfoTool:
    def __init__(self, filename):
        self.API_KEY = '3bf9939c'
        self.filename = filename
        self.header, self.input = open_csv(self.filename, ';')

    def __get_field_from_entry(self, entry, field):
        if field in self.header and entry[self.header.index(field)]:
            return entry[self.header.index(field)]
        return None

    def __put_info_in_entry_field(self, entry, field, value):
        if not value:
            return
        field_info = self.__get_field_from_entry(entry, field)
        if not field_info:
            entry[self.header.index(field)] = value

    def __entry_has_all_fields(self, entry):
        for field in self.header:
            if field in ('flags', 'user', 'checks', 'imdb'):
                continue
            if not entry[self.header.index(field)]:
                return False
        return True

    def add_info_to_csv(self):
        for key, entry in enumerate(self.input):
            if not self.__get_field_from_entry(entry, 'imdb'):
                continue
            imdb_link = self.__get_field_from_entry(entry, 'imdb')
            imdb_id = get_imdb_id_from_url(imdb_link)
            if not imdb_id:
                continue
            if not self.__entry_has_all_fields(entry):

                response = self.get_info_from_omdb_by_imdb_id(imdb_id)
                for field in self.header:
                    if field in ('flags', 'user', 'checks', 'imdb'):
                        continue
                    value = response[field] if field in response else None
                    self.__put_info_in_entry_field(entry, field, value)

        self.__save_extended_csv_to_file()

    def __save_extended_csv_to_file(self):
        with open(self.filename, 'w+', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile, delimiter=';')
            writer.writerow(self.header)
            writer.writerows(self.input)

    def get_info_from_omdb_by_imdb_id(self, imdb_id):
        req_url = f"http://www.omdbapi.com/?i={imdb_id}&apikey={self.API_KEY}"
        response = requests.post(req_url)
        if 'Error' in response.json():
            print(response.json()['Error'], imdb_id)
            return None

        return response.json()


class IcmChallengeTool:
    def __init__(self, header, challenge_list, use_checks=False, use_nominations=False):
        self.header = header
        self.challenge_list = challenge_list
        self.users = self.__create_users_dict()
        self.use_nominations = use_nominations
        self.use_checks = use_checks
        # if self.use_nominations:
        #     self.__map_nominations_to_users()
        self.fivehundred, self.thousand = self.__get_500_list()
        self.users['overall'] = self.get_overall()

    def __get_field_from_entry(self, entry, field):
        if field in self.header and entry[self.header.index(field)]:
            return entry[self.header.index(field)]
        return None

    def __get_500_list(self):
        _, lst = open_csv('1000.csv', ',', encoding='latin-1')
        fivehundred = list()
        thousand = list()
        for rank, entry in enumerate(lst):
            imdb = get_imdb_id_from_url(entry[11])
            if rank < 500:
                fivehundred.append(imdb)
            else:
                thousand.append(imdb)

        return fivehundred, thousand

    def __create_users_dict(self):
        users = dict()
        for entry in self.challenge_list:
            user = self.__get_field_from_entry(entry, 'user')
            if user not in users:
                users[user] = {
                    'count': 0,
                    # 'check_counts': list(),
                    'imdb_ids': list()
                }
            flags = self.__get_field_from_entry(entry, 'flags')
            if flags and not ('s' in flags and 'c' not in flags):
                users[user]['count'] += 1
            # if entry[CHECKS]:
            #     users[user]['check_counts'].append(int(entry[CHECKS]))
            imdb_id = get_imdb_id_from_url(self.__get_field_from_entry(entry, 'imdb'))
            if imdb_id:
                users[user]['imdb_ids'].append(imdb_id)

        return users

    # def __map_nominations_to_users(self):
    #     mappings = open_yaml('nominations')
    #     for username, val in self.users.items():
    #         val['nomination'] = {
    #             'link': mappings[username]['link'] if username in mappings else None,
    #             'id': mappings[username]['id'] if username in mappings else None
    #         }

    def get_overall(self):
        overall = {'count': sum(user['count'] for _, user in self.users.items()),
                   # 'check_counts': list(),
                   'imdb_ids': list(),
                   # 'nomination':
                   #     {'link': list(),
                   #      'id': list()}
                   }
        # overall['check_counts'].extend(
        #     check_count for _, user in self.users.items() for check_count in user['check_counts'])
        overall['imdb_ids'].extend(
            imdb_id for _, user in self.users.items() for imdb_id in user['imdb_ids'])
        # if self.use_nominations:
        #     overall['nomination']['link'].extend(
        #         user['nomination']['link'] for _, user in self.users.items() if user['nomination'])
        #     overall['nomination']['id'].extend(
        #         user['nomination']['id'] for _, user in self.users.items() if user['nomination'])
        return overall

    def get_leader_list(self):
        def take_second(elem):
            return elem[1]

        def take_lower(elem):
            return str.casefold(elem[0])

        user_count_list = [(user_name, user['count']) for user_name, user in self.users.items()]
        user_count_list = sorted(user_count_list, key=take_lower)
        return sorted(user_count_list, key=take_second, reverse=True)

    def get_most_frequent_movies(self, minimum_frequency):
        counter = Counter(self.users['overall']['imdb_ids'])
        result = counter.most_common()
        return [x for x in result if x[1] >= minimum_frequency]

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
                      f"{'[td][b]Check count: Mean[/b][/td][td][b]Median[/b][/td]' if self.use_checks else ''}" \
                      f"[td][b]500<400[/b][/td][td][b]501-1000[/b][/td][td][b]neither[/b][/td]" \
                      f"{'[td][b]1 > 500 < 400[/ b][/ td][td][b]nom.watched by[/ b][/ td][td][b]user watches[/ b][/ td]' if self.use_nominations else ''}" \
                      f"[/tr]\n"
        overall_row = ''
        last_count = 100000
        last_i = 0
        for i, (username, count) in enumerate(leader_list):
            row = f"[tr][td]\t{self.__get_position(count, i, last_count, last_i)}\t[/td]" \
                  f"[td]\t{username}\t[/td]" \
                  f"[td]\t{count}\t[/td]"
            # row += self.__get_check_stats_cell(username)
            row += self.__get_500_400_cell(username)
            # row += self.__get_nomination_cell(username)
            row += f"[/tr]\n"
            if last_count > count:
                last_i = i
                last_count = count

            if i == 0:
                overall_row = row
            else:
                leaderboard += row

        leaderboard += overall_row + '[/table]'
        return leaderboard

    def print_table_of_most_frequent_entries(self, minimum_freq):
        most_freq_list = self.get_most_frequent_movies(minimum_freq)
        table = f"[table]\n[tr][td][b]\tTimes challenged\t[/b][/td][td][b]\tName\t[/b][/td][td][b]\tYear\t[/b][/td]" \
                f"[td][b]IMDB[/b][/td][td][b]ICM[/b][/td][/tr]\n"
        for imdb_id, count in most_freq_list:
            title, year = self.__get_title_and_year_from_imdb_id(imdb_id)
            row = f"[tr][td]\t{count}\t[/td]" \
                  f"[td]\t{title}\t[/td]" \
                  f"[td]\t{year}\t[/td]" \
                  f"[td]\t[url=https://www.imdb.com/title/{imdb_id}/] :imdb: [/url]\t[/td]" \
                  f"[td]\t[url=https://www.icheckmovies.com/search/movies/?query={imdb_id}/] :ICM: [/url]\t[/td]" \
                  f"[/tr]\n"
            table += row

        table += '[/table]'
        return table

    def __get_position(self, count, i, last_count, last_i):
        if i == 0:
            return '-'
        elif count == last_count:
            return last_i
        else:
            return i

    # def __get_nomination_cell(self, username):
    #     if not self.use_nominations:
    #         return ''
    #     nomination = self.users[username]['nomination']
    #     nominations_watched_by_user_count = self.__get_user_nomination_watches_count(username)
    #     if type(nomination['link']) == str:
    #         result = f"[td]\t[url={nomination['link']}] :ICM: [/url]\t[/td]" \
    #                  f"[td]\t{self.__get_nomination_watched_by_count(username)}\t[/td]"
    #     elif type(nomination) == list:
    #         result = f"[td]\t{len(nomination)}x\t[/td][td]\t-\t[/td]"
    #     else:
    #         result = f"[td]\t-\t[/td][td]\t-\t[/td]"
    #     return f"{result}[td]\t{nominations_watched_by_user_count}\t[/td]"

    def __get_500_400_cell(self, username):
        return f"[td]\t{self.get_count_of_entries_in_500(username)}\t[/td]" \
               f"[td]\t{self.get_count_of_entries_in_1000(username)}\t[/td]" \
               f"[td]\t{self.get_count_of_entries_not_in_top_list(username)}\t[/td]"

    # def __get_check_stats_cell(self, username):
    #     if not self.use_checks:
    #         return ''
    #     return f"[td]\t{self.get_check_count_mean(username):.1f}\t[/td]" \
    #            f"[td]\t{self.get_check_count_median(username):.1f}\t[/td]"

    # def __get_nomination_watched_by_count(self, username):
    #     all_watches = self.users['overall']['imdb_ids']
    #     user_nomination = self.users[username]['nomination']['id']
    #     return all_watches.count(user_nomination)
    #
    # def __get_user_nomination_watches_count(self, username):
    #     all_nominations = self.users['overall']['nomination']['id']
    #     user_watches = self.users[username]['imdb_ids']
    #     return len([x for x in user_watches if x in all_nominations])

    # def get_check_count_mean(self, username):
    #     if self.users[username]['check_counts']:
    #         return statistics.mean(self.users[username]['check_counts'])
    #     return 0
    #
    # def get_check_count_median(self, username):
    #     if self.users[username]['check_counts']:
    #         return statistics.median(self.users[username]['check_counts'])
    #     return 0

    def __get_title_and_year_from_imdb_id(self, imdb_id):
        for entry in self.challenge_list:
            if get_imdb_id_from_url(self.__get_field_from_entry(entry, 'imdb')) == imdb_id:
                return self.__get_field_from_entry(entry, 'Title'), self.__get_field_from_entry(entry, 'Year')
        return None, None

    def get_yearly_breakdown(self):
        yearly_counts = dict()
        for _, entry in enumerate(self.challenge_list):
            year = self.__get_field_from_entry(entry, 'Year')
            if year:
                year = year[0:4]
                yearly_counts[year] = yearly_counts[year] + 1 if year in yearly_counts else 1
        yearly_breakdown = [(year, count) for year, count in yearly_counts.items()]
        return sorted(yearly_breakdown)

    def get_decade_breakdown(self):
        yearly_breakdown = self.get_yearly_breakdown()
        decade_counts = dict()
        for year, count in yearly_breakdown:
            decade = year[0:3] + '0s'
            decade_counts[decade] = decade_counts[decade] + count if decade in decade_counts else count
        return [(decade, count) for decade, count in decade_counts.items()]

    def print_decade_breakdown(self):
        decade_breakdown = self.get_decade_breakdown()
        table = f"[table]\n[tr][td][b]\tDecade\t[/b][/td][td][b]\tCount\t[/b][/td][/tr]\n"
        for decade, count in decade_breakdown:
            table += f"[tr][td]\t{decade}\t[/td][td]\t{count}\t[/td][/tr]\n"
        table += "[/table]"
        return table

    def get_misc_field_breakdown(self, field):
        field_counts = dict()
        for _, entry in enumerate(self.challenge_list):
            field_values = self.__get_field_from_entry(entry, field)
            if not field_values:
                continue
            field_values = field_values.split(', ')
            for field_value in field_values:
                if field_value == 'N/A':
                    continue
                field_counts[field_value] = field_counts[field_value] + 1 if field_value in field_counts else 1
        field_breakdown = [(field_value, count) for field_value, count in field_counts.items()]
        return sorted(field_breakdown)

    def print_misc_field_breakdown_table(self, field):
        def take_second(elem):
            return elem[1]

        field_breakdown = self.get_misc_field_breakdown(field)
        field_breakdown = sorted(field_breakdown, key=take_second, reverse=True)
        table = f"[table={field} Breakdown]\n[tr][td][b]\t{field}\t[/b][/td][td][b]\tCount\t[/b][/td][/tr]\n"
        for field_value, count in field_breakdown:
            table += f"[tr][td]\t{field_value}\t[/td][td]\t{count}\t[/td][/tr]\n"
        table += "[/table]"
        return table


if __name__ == '__main__':
    ot = OMDBInfoTool('russia.csv')
    ot.add_info_to_csv()
    header, challenge_list = open_csv('russia.csv', ';')
    ct = IcmChallengeTool(header, challenge_list)
    table = f"{ct.print_leaderboard()}\n" \
            f"\nDecade breakdown:" \
            f"{ct.print_decade_breakdown()}\n" \
            f"\n{ct.print_misc_field_breakdown_table('Director')}\n" \
            f"\n\n[spoiler=Movies that have been challenged more than once]" \
            f"{ct.print_table_of_most_frequent_entries(2)}\n[/spoiler]"
    print(table)
    write_to_clipboard_mac(table)
    # print(ct.print_country_breakdown_table())
