import os
import sys
import yaml
from argparse import ArgumentParser
from pyclarity_lims.lims import Lims

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from integration_tests.test_entities import generate_entities_expected_output, test_all_entities


def main():
    a = ArgumentParser()
    a.add_argument('--url', type=str)
    a.add_argument('--username', type=str)
    a.add_argument('--password', type=str)
    a.add_argument('--config', type=str, required=True)
    a.add_argument('--generate_config', action='store_true')
    args = a.parse_args()

    config = {}
    if os.path.isfile(args.config):
        with open(args.config, 'r') as open_file:
            config = yaml.load(open_file)

    url = args.url or config.get('clarity', {}).get('url')
    if not url:
        print('Specify url on the command line')
        a.print_help()
        return 1
    username = args.username or config.get('clarity', {}).get('username')
    if not username:
        print('Specify username on the command line')
        a.print_help()
        return 1
    password = args.password or config.get('clarity', {}).get('password')
    if not password:
        print('Specify password on the command line')
        a.print_help()
        return 1

    lims = Lims(baseuri=url, username=username, password=password)

    if args.generate_config:
        config['entities'] = generate_entities_expected_output(lims)
        with open(args.config, 'w') as open_file:
            yaml.dump(config, open_file, width=180, indent=4)
    else:
        test_all_entities(lims, config.get('entities', {}))


if __name__ == '__main__':
    sys.exit(main())
