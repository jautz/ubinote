# Ubiquitous Notebook

## Abstract

A web application that lets you file notes into categories.
It has a minimalistic wiki-like markup that allows basic formatting and
turns URIs in the note's text into hyperlinks.

## Requirements

* Perl CGI (tested with Apache)
* Database (tested with MySQL and MariaDB)

## Setup

* Use mkschema.sh to generate the sql statements to create the tables.
* Execute the sql statements from your DB admin console.
* Follow the instructions in the example config file `.ubinote`.
* Specify the CSS file to use in `.ubinote` (see `style.css` for an example).
* Copy the index.cgi to an appropriate folder on your webserver. Feel free to
  rename it. I chose this name because it usually works as default page name.

## Security

I _highly recommend_ that you restrict access to this application, e.g. by using a `.htaccess` file.
It has been developed for a for a small group of trusted users.
It is not meant to be used on the public internet unless you implement more security-related checks.

## Migration to UTF-8

Since September 10, 2023 the project uses UTF-8.
The former "charset" configuration has no effect anymore.

The recommended way to migrate an existing setup is this:
* Take down the old CGI script.
* Dump the database with a tool like mysqldump into a UTF-8 encoded text file.
* Strip the dump to only contain the INSERT ... VALUES statements.
* Create a new DB and new tables, all using charset "utf8mb4" (see schema-template.mysql).
* Apply the INSERT statements.
* Set up the new CGI script.
