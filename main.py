#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import re
import os
import yaml
import arxiv
import json
from notion_client import Client


def read_yaml(file_path):
    """Reads the 'config.yaml' file and returns the `notion_token` and `database_id`."""
    with open(file_path, 'r') as f:
        print("Reading the config file...")
        config_dict = yaml.load(f, Loader=yaml.FullLoader)
        notion_token = config_dict['NOTION_TOKEN']
        database_id = config_dict['DATABASE_ID']
        page_info = config_dict['PROPERTY']
        return notion_token, database_id, page_info


def init_notion(notion_token):
    """Initializes a `notion_client.Client` object."""
    # Initialize a client object
    client = Client(auth=notion_token)

    return client


def read_database(client, database_id, title_property='title', url_property='url'):
    """Reads the database and returns the dicts of property values."""
    print("Reading the database from Notion...")
    results = client.databases.query(
        **{
            "database_id": database_id,
        }
    ).get("results")

    value_ls = {}
    for result in results:
        page_id = result['id']
        paper_pdf_url = result['properties'][url_property]['url']
        if paper_pdf_url is not None:
            paper_title = result['properties'][title_property]['title'][0]['plain_text']
            value_ls.update({paper_title: [page_id, paper_pdf_url]})

    return value_ls


def get_paper_infos(pdf_urls):
    """Gets the paper information from the arxiv API and returns the paper info."""
    print("Getting the paper information from arXiv...")
    paper_urls = {}

    for key, value in pdf_urls.items():
        # extract the arxiv id from the pdf url using regular expressions
        match = re.search(r"\d{4}\.\d{5}", value[1])
        if match:
            arxiv_id = match.group(0)
            # Construct the paper URL using the arXiv ID
            paper_url = f"https://arxiv.org/abs/{arxiv_id}"
            paper_urls[key] = [value[0], paper_url]

    paper_infos = {}

    for key, value in paper_urls.items():
        # Extract the arXiv ID from the paper URL
        arxiv_id = value[1].split("/")[-1]
        search = arxiv.Search(id_list=[arxiv_id])
        paper = next(search.results())
        title = paper.title
        authors = [author.name for author in paper.authors]
        abstract = paper.summary
        paper_infos[key] = {"title": title,
                            "authors": authors, "abstract": abstract, "page_id": value[0]}

    with open("paper_infos.json", "w") as f:
        json.dump(paper_infos, f, indent=2)

    print("Paper information saved to 'paper_infos.json'.")
    return paper_infos


def get_paper_authors(paper_infos):
    """Gets the paper authors and returns the paper authors."""
    paper_authors = {}
    for key, value in paper_infos.items():
        paper_authors[key] = [value["page_id"], value["authors"]]
    return paper_authors


def write_database(database_id, client, paper_authors, title_property="title", author_property="author"):
    """Writes the paper authors to the database."""
    print("Updating the database with the author information...")
    new_authors = []
    page_ids = []
    for title, value in paper_authors.items():
        author_names = []
        for author in value[1]:
            author_names.append({
                "text": {
                    "content": author
                }
            })
        new_authors.append({
            title_property: {
                "title": [
                    {
                        "text": {
                            "content": title
                        }
                    }
                ]
            },
            author_property: {
                "multi_select": [{"name": author} for author in value[1]]
            }
        })
        page_ids.append(value[0])
    for idx, author in enumerate(new_authors):
        client.pages.update(page_id=page_ids[idx], parent={
                            "database_id": database_id}, properties=author)

    print("Database updated successfully!")


def main():
    # Get the path of the current file
    pwd = os.path.dirname(os.path.abspath(__file__))
    yaml_path = os.path.join(pwd, 'config.yaml')

    # Read the config file
    notion_token, database_id, page_info = read_yaml(yaml_path)
    title_property, url_property, author_property = page_info[
        'title'], page_info['url'], page_info['author']

    # Initialize the notion client
    client = init_notion(notion_token)

    # Get the paper information from arxiv
    pdf_urls = read_database(client, database_id, title_property, url_property)
    paper_infos = get_paper_infos(pdf_urls)
    paper_authors = get_paper_authors(paper_infos)

    # Write the paper information to the database
    write_database(database_id, client, paper_authors,
                   title_property, author_property)


if __name__ == '__main__':
    main()
