import pprint

print = pprint.pprint
import glob
import os
import yaml

FAMILIES_DIR = './families'


def extract_people(families):
  return [person for family in families for person in family['People']]


def read_families(root):
  families = [
      *glob.glob(os.path.join(root, '*.yaml')),
      *glob.glob(os.path.join(root, '*.yml')),
  ]
  return [read_family(family) for family in families]


def read_family(path):
  with open(path, 'r') as f:
    return yaml.safe_load(f)


if __name__ == '__main__':
  print('=' * 80)
  families = read_families('./families')
  people = extract_people(families)
  print(people[0])
