# Ubiquitous Notebook

## Abstract

A web application that lets you file notes into categories.
It has a minimalistic wiki-like markup that allows basic formatting and
turns URIs in the note's text into hyperlinks.

## Requirements

* Perl CGI (tested with Apache)
* Database (tested with MySQL)

## Setup

* Use mkschema.sh to generate the sql statements to create the tables.
* Execute the sql statements from your DB admin console.
* Follow the instructions in the example config file `.ubinote`.
* Copy the index.cgi to an appropriate folder on your webserver. Feel free to
  rename it. I chose this name because it usually works as default page name.
* I recommend to restrict access to this folder, e.g. .htaccess basic auth.
