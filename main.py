import json
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

import requests

CONFIG_PATH = 'config.json'

class GitLab:
    weights = ('0', '1', '2', '3', '5', '8', '13', '21', '34', '55', '89')
    def __init__(self, config_path=CONFIG_PATH) -> None:
        with open(config_path) as f: self.config = json.load(f)
        self.link = f'{self.config["link"]}/api/v4'
        self.access_token_link = f'?access_token={self.config["access_token"]}'
        if not self.config.get('project_id'):
            self.get_project_id()
            with open(config_path, 'w') as f: json.dump(self.config, f, indent=4)

    def get_project_id(self):
        link = f'{self.link}/projects{self.access_token_link}&search_namespaces=true&search={self.config["project_path"]}'
        res = requests.get(link)
        self.config['project_id'] = res.json()[0].get('id')

    def get_issues_from_open_milestones(self):
        link = f'{self.link}/projects/{self.config["project_id"]}/issues{self.access_token_link}&milestone_id=Started'
        res = requests.get(link)
        return res.json()

    def calculate_weights(self, issues, from_label=True):
        open = 0
        total = 0
        closed = []
        start = datetime.strptime(
                        issues[0]['milestone']['start_date'],
                        '%Y-%m-%d'
                    )
        end = datetime.strptime(
                    issues[0]['milestone']['due_date'],
                    '%Y-%m-%d'
                )

        for issue in issues:
            if from_label:
                weight = 0
                for label in issue['labels']:
                    if label not in self.weights:
                        continue

                    weight = int(label)
                    break

            else: # from title
                weight = int(issue['title'].split('-')[0])

            total += weight

            if issue['state'] == 'opened':
                open += weight

            elif issue['state'] == 'closed':
                closed.append(
                    (
                        datetime.strptime(
                            issue['closed_at'].split('T')[0],
                            '%Y-%m-%d'
                        ),
                        weight
                    )
                )

        closed.sort(key=lambda x: x[0])
        dates= []
        weights = []
        current = total
        for date, weight in closed:
            dates.append(date)
            weights.append(current := current - weight)

        weights.insert(0, total)
        dates.insert(0, start)
        return (start, end, (total, open, (dates, weights)))

def create_burndown_chart(start, end, weights):
    fig = plt.figure()
    ax = fig.add_subplot(1,1,1)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
    ax.axis((start, end, 0, weights[0]))
    plt.setp(ax.get_xticklabels(), rotation = 15)
    ax.plot((start, end), (weights[0], 0))
    ax.plot(*weights[2], marker='o')
    plt.savefig('output.png')

if __name__ == "__main__":
    gitlab = GitLab()
    issues = gitlab.get_issues_from_open_milestones()
    with open('out.json', 'w') as f:
        f.write(json.dumps(issues,indent=2))
    # print(json.dumps(issues)
    weights = gitlab.calculate_weights(issues)
    create_burndown_chart(*weights)
