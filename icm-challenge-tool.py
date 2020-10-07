import csv, yaml
import os
import statistics
import requests
import subprocess
from collections import Counter
import glob


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


def yield_lists(challenge_name):
    os.chdir(f"icm_lists/{challenge_name}/")
    for filename in sorted(glob.glob(f"*.csv")):
        yield filename[:-len('.csv')], os.path.join(os.getcwd(), filename)


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
        if not self.__get_field_from_entry(entry, field):
            if field == 'Runtime':
                value = value[0:-len(' min')]
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
    def __init__(self, header, challenge_list, challenge_name):
        self.challenge_name = challenge_name
        self.header = header
        self.challenge_list = challenge_list
        self.users = self.__create_users_dict()
        self.icm_lists = self.__get_all_icm_lists()
        self.users['overall'] = self.get_overall()

    def __get_field_from_entry(self, entry, field):
        if field in self.header and entry[self.header.index(field)]:
            return entry[self.header.index(field)]
        return None

    def __get_all_icm_lists(self):
        icm_lists = dict()
        for list_name, icm_list in yield_lists(self.challenge_name):
            _, lst = open_csv(icm_list, ',', encoding='latin-1')
            imdb_ids = list()
            for rank, entry in enumerate(lst):
                imdb = get_imdb_id_from_url(entry[11])
                imdb_ids.append(imdb) if imdb else None
            icm_lists[list_name] = imdb_ids if imdb_ids else None
        return icm_lists

    def __create_users_dict(self):
        users = dict()
        for entry in self.challenge_list:
            user = self.__get_field_from_entry(entry, 'user')
            if user not in users:
                users[user] = {
                    'count': 0,
                    'imdb_ids': list(),
                    'runtime': 0
                }
            if self.does_entry_increase_count(entry):
                users[user]['count'] += 1
            users[user]['runtime'] += self.__get_runtime_from_entry(entry)
            imdb_id = get_imdb_id_from_url(self.__get_field_from_entry(entry, 'imdb'))
            if imdb_id:
                users[user]['imdb_ids'].append(imdb_id)

        return users

    def __get_runtime_from_entry(self, entry):
        flags = self.__get_field_from_entry(entry, 'flags')
        if flags and 'm' in flags:
            return 0
        runtime = self.__get_field_from_entry(entry, 'Runtime')
        if runtime:
            return int(runtime)
        elif 'Runtime' in self.header:
            if flags and 's' in flags:
                return 5
            else:
                return 40

    def does_entry_increase_count(self, entry):
        flags = self.__get_field_from_entry(entry, 'flags')
        if flags and 's' in flags and 'c' not in flags:
            return False
        return True

    def get_overall(self):
        overall = {'count': sum(user['count'] for _, user in self.users.items()),
                   'imdb_ids': list(),
                   'runtime': sum(user['runtime'] for _, user in self.users.items())
                   }
        overall['imdb_ids'].extend(
            imdb_id for _, user in self.users.items() for imdb_id in user['imdb_ids'])
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

    def get_count_of_entries_in_icm_list(self, username, list_name):
        imdbs = [imdb for imdb in self.users[username]['imdb_ids'] if imdb in self.icm_lists[list_name]]
        return len(imdbs)

    def get_user_runtime_cell(self, username):
        if self.users['overall']['runtime'] <= 0:
            return ''
        else:
            return f"[td]\t{self.users[username]['runtime']}\t[/td]"

    def print_leaderboard(self):
        leader_list = self.get_leader_list()
        leaderboard = f"[table]\n[tr][td][b]\tRank\t[/b][/td][td][b]\tParticipant\t[/b][/td][td][b]\tCount\t[/b][/td]"
        leaderboard += f"[td][b]\tMinutes\t[/b][/td]" if 'Runtime' in self.header else ''
        leaderboard += f"{self.__get_icm_list_name_cells()}"
        leaderboard += f"[/tr]\n"
        overall_row = ''
        last_count = 100000
        last_i = 0
        for i, (username, count) in enumerate(leader_list):
            row = f"[tr][td]\t{self.__get_position(count, i, last_count, last_i)}\t[/td]" \
                  f"[td]\t{username}\t[/td]" \
                  f"[td]\t{count}\t[/td]"
            row += self.get_user_runtime_cell(username)
            row += self.__get_count_in_icm_list_cells(username)
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

    def __get_icm_list_name_cells(self):
        result = ''
        for list_name in self.icm_lists:
            result += f"[td][b]\t{list_name}\t[/b][/td]"
        return result

    def __get_count_in_icm_list_cells(self, username):
        result = ''
        for list_name in self.icm_lists:
            result += f"[td]\t{self.get_count_of_entries_in_icm_list(username, list_name)}\t[/td]"
        return result

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

    def print_misc_field_breakdown_table(self, field, min_value=1):
        def take_second(elem):
            return elem[1]

        field_breakdown = self.get_misc_field_breakdown(field)
        field_breakdown = sorted(field_breakdown, key=take_second, reverse=True)
        table = f"[table]\n[tr][td][b]\t{field}\t[/b][/td][td][b]\tCount\t[/b][/td][/tr]\n"
        for field_value, count in field_breakdown:
            if count < min_value:
                continue
            table += f"[tr][td]\t{field_value}\t[/td][td]\t{count}\t[/td][/tr]\n"
        table += "[/table]"
        return table

    def __get_alphabetical_user_list(self):
        def take_lower(elem):
            return str.casefold(elem[0])

        user_list = [user_name for user_name in self.users if user_name != 'overall']
        return sorted(user_list, key=take_lower)

    def get_misc_field_count_for_value_for_user(self, user, field, value):
        all_entries_for_field = [self.__get_field_from_entry(entry, field) for _, entry in
                                 enumerate(self.challenge_list)
                                 if not user or self.__get_field_from_entry(entry, 'user') == user]
        return len([1 for i in all_entries_for_field if value in i])

    def print_misc_field_breakdown_table_by_user(self, field, allowed_values):
        user_list = self.__get_alphabetical_user_list()
        table = f"[table]\n[tr][td][b]\tusername\t[/b][/td]"
        for val in allowed_values:
            table += f"[td][b]\t{val}\t[/b][/td]"
        table += "[/tr]\n"

        for user_name in user_list:
            table += f"[tr][td][b]\t{user_name}\t[/b][/td]"
            for val in allowed_values:
                table += f"[td]\t{self.get_misc_field_count_for_value_for_user(user_name, field, val)}\t[/td]"
            table += f"[/tr]\n"

        table += f"[tr][td][b]\tOverall\t[/b][/td]"
        for val in allowed_values:
            table += f"[td]\t{self.get_misc_field_count_for_value_for_user(None, field, val)}\t[/td]"
        table += f"[/tr]\n[/table]"
        return table


if __name__ == '__main__':
    challenge_name = 'southeastasia'
    country_list = ['Brunei', 'Cambodia', 'Indonesia', 'Laos', 'Malaysia',
                    'Myanmar', 'Philippines', 'Singapore', 'Thailand', 'Timor-Leste', 'Vietnam']
    ot = OMDBInfoTool(f"{challenge_name}.csv")
    ot.add_info_to_csv()
    header, challenge_list = open_csv(f"{challenge_name}.csv", ';')
    ct = IcmChallengeTool(header, challenge_list, challenge_name)
    table = f"{ct.print_leaderboard()}\n"
    table += f"\nCountry breakdown:\n{ct.print_misc_field_breakdown_table_by_user('Country', country_list)}\n"
    table += f"\nDecade breakdown:{ct.print_decade_breakdown()}\n"
    table += f"\n[spoiler=Director breakdown]{ct.print_misc_field_breakdown_table('Director', 2)}[/spoiler]\n"
    table += f"\n\n[spoiler=Movies that have been challenged more than once]"
    table += f"{ct.print_table_of_most_frequent_entries(2)}\n[/spoiler]"
    print(table)
    write_to_clipboard_mac(table)
