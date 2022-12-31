"""Turns v1 data into People data.

We'll take an additive approach to this - pulling in all data from any format of "person" in the old info that we can find.

We also don't want to lose anything, so we'll be super noisy if there's any data that we don't understand, but quiet otherwise.
"""
import collections
import re
from typing import Optional, Tuple
import bs4
import glob
import os
import unittest


def clean_name(line_text, relation):
  if relation == 'husband':
    return re.sub(r'^Husband ', '', line_text.strip()).strip()
  if relation == 'wife':
    return re.sub(r'^Wife ', '', line_text.strip()).strip()
  if relation == 'child':
    return re.sub(r'\d\s+[MF]', '', line_text.strip()).strip()
  raise ValueError(f'unsupported name relation: {relation}')


def get_href(soup: bs4.BeautifulSoup) -> Optional[str]:
  if not (anchor := soup.find('a')):
    return None
  if not (href := anchor.attrs.get('href')):
    return None
  return href


class PersonRef:
  link = ''
  name = ''
  relation = ''
  family = ''
  file = ''
  content = []

  def __init__(self, relation: str, soup: bs4.BeautifulSoup):
    self.link = get_href(soup)
    self.name = clean_name(soup.text, relation)
    self.relation = relation
    self.content = []
    self.family = ''
    self.file = ''

  def __repr__(self):
    return f'<{self.name}>'

  def to_dict(self):
    return {
        'link': self.link,
        'name': self.name,
        'relation': self.relation,
        'family': self.family,
        'content': [c.to_dict() for c in self.content]
    }


def iter_files(pattern):
  for path in glob.glob(pattern):
    with open(path, 'r') as file:
      try:
        yield path, file.readlines()
      except Exception as e:
        print(f'Unable to read: {path} ({e})')


def read_start_of_person(line) -> Optional[PersonRef]:
  soup = bs4.BeautifulSoup(line, 'html.parser')
  if soup.text.startswith('Husband'):
    return PersonRef('husband', soup)
  if soup.text.startswith('Wife'):
    return PersonRef('wife', soup)
  if re.match(r'\d\s+[MF]', soup.text):
    return PersonRef('child', soup)
  return None


def is_end_of_file(line):
  if 'Table of Contents' in line:
    return True
  return False


class PersonContent:
  key = None
  value = None
  href = None

  def __init__(self, soup, text):
    self.href = get_href(soup)
    data = text.split(':', 1)
    if len(data) == 2:
      self.key = data[0].strip()
      self.value = data[1].strip()
    elif data[0]:
      self.value = data[0].strip()

  def __repr__(self):
    return f'{self.key}: {self.value} ({self.link})'

  def to_dict(self):
    return {
        'key': self.key,
        'value': self.value,
        'href': self.href,
    }


def read_person_content(line):
  soup = bs4.BeautifulSoup(line, 'html.parser')
  text = soup.text.strip()
  if not text:
    return None
  return PersonContent(soup, text)


def read_family_anchor(line):
  soup = bs4.BeautifulSoup(line, 'html.parser')
  if not (anchor := soup.find('a')):
    return None
  if not (name := anchor.attrs.get('name')):
    return None
  if not re.fullmatch(r'^f\d+', name):
    print(f'Warning - skipping weird family anchor: {name}')
    return None
  return name


def iter_people(lines):
  """Loop over person information in "f" file content, e.g. f10.htm."""
  current_ref = None
  current_family = None
  for line in lines:
    if family := read_family_anchor(line):
      current_family = family
    if is_end_of_file(line):
      if current_ref:
        yield current_ref
      break
    ref = read_start_of_person(line)
    if ref and current_ref:
      yield current_ref
    if ref:
      current_ref = ref
      if current_family:
        current_ref.family = current_family
      continue
    if not current_ref:
      continue
    if line_content := read_person_content(line):
      current_ref.content.append(line_content)

def iter_all_people():
  for path, lines in iter_files('../v1/individual/f?.htm'):
    for person in iter_people(lines):
      person.file = os.path.basename(path)
      yield person

def _frequencies(data):
  results = collections.defaultdict(lambda: 0)
  for data in data:
    results[data] += 1
  return results

def _gendex_families():
  with open('../v1/individual/gendex.txt', 'r') as gendex:
    for line in gendex:
      family = line.split('|')[0]
      if not family:
        continue
      yield family


def _diff_frequencies(a, b):
  c = collections.defaultdict(lambda: 0, a)
  for key, value in b.items():
    c[key] -= value
  return c

if __name__ == '__main__':
  print('=' * 80)

class ExtractTests(unittest.TestCase):
  def test_families_match_gendex(self):
    read_families = [
      f'{person.file}#{person.family}'
      for person in iter_all_people()
    ]

    gendex_families = [
      f'{person.file}#{person.family}'
      for person in iter_all_people()
    ]

    read = _frequencies(read_families)
    gendex = _frequencies(gendex_families)
    self.assertEqual({k: v
                      for k, v
                      in _diff_frequencies(gendex, read).items()
                      if v
                      }, {})
    self.assertEqual({k: v
                      for k, v
                      in _diff_frequencies(read, gendex).items()
                      if v}, {})

