#
# Copyright (c) 2011 Per Andersson
#
# This file is part of mlogr.
#
# mlogr is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# mlogr is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with mlogr.  If not, see <http://www.gnu.org/licenses/>.
#

import codecs, datetime, getopt, os, re, sqlite3, sys, yaml

import exception


class Config(object):
    """
    Parse and store configuration.
    """

    # valid configuration details
    re_valid_tablename = "^[\w_]+$"
    re_valid_columnname = "^[\w_]+$"
    valid_types = ["boolean", "integer", "real", "text"]

    def __init__(self, configfile = None):
        """
        Constructor for Config object.
        """
        if not os.path.isfile(configfile):
            raise exception.NoConfigFile(configfile)
        self.configfile = configfile

        self.parse()


    def parse(self):
        """
        Parse config file and store results.
        """
        # load config file
        self.raw_config = yaml.load(file(self.configfile, "r").read())

        if mlogr.DEBUG:
            print "DEBUG: raw_config =", self.raw_config

        # tables
        self.tables = self.raw_config["tables"]
        if mlogr.DEBUG:
            print "DEBUG: tables=", self.tables

        # extract table definitions (copy raw config and del tables)
        self.table_defs = self.raw_config
        del self.table_defs["tables"]
        if mlogr.DEBUG:
            print "DEBUG: table_defs=", self.table_defs

        # check sanity of config

        # check sanity of table and column names

        # no duplicate table names
        if not len(set(self.tables)) == len(self.tables):
            raise exception.DuplicateTable(None)

        # listed tables should be defined
        for table in self.tables:
            if not re.search(self.re_valid_tablename, table):
                raise exception.BadTableName(table)
            if table not in self.table_defs.keys():
                raise exception. \
                        TableMissingDef(table)

        # for every table_def check every column name and type
        for table in self.table_defs:
            for column, type in self.table_defs[table].iteritems():
                if not re.search(self.re_valid_columnname, column):
                    raise exception.BadColumnName(column)

                if type not in self.valid_types:
                    raise exception.BadColumnType(column, type)

        # config is sane, store it
        self.config = {"tables": self.tables, "table_defs": self.table_defs}


    def print_config(self):
        """
        Print parsed configuration.
        """
        print unicode(yaml.dump(self.config))



class mlogr(object):
    """Usage: mlogr [OPTIONS]...

    -c, --config-file=FILE  use supplied config file.
    -d, --debug             print debugging information.
    -f, --file=FILE         use supplied database, can also be set in the
                            config file.
    -p, --print-config      print configured log tables.
    -h, --help              print this help and exit.
    """

    def __init__(self, args):
        """
        Constructor method. Entry point for program.
        """
        # parse command line options
        self.args = args
        self.parse_opts()

        print "Reading configuration from %s..." % self.configfile
        self.config = Config(self.configfile)

        print "Connecting to database %s..." % self.file
        self.conn = sqlite3.connect(self.file)

        # create log tables defined in config if it they don't exist.
        self.create_tables()

        # ask user for input
        self.input_loop()

        # ask user to check given input
        self.validate_input()

        print "\nWriting entered values to database..."
        self.write_to_db()

        # close database connection
        self.conn.close()

        self.run_posthook()

        print "Done!"

        sys.exit(0)


    @staticmethod
    def usage():
        print mlogr.__doc__


    def parse_opts(self):
        """
        Parse command line options.
        """
        try:
            opts, cl_args = \
                getopt.getopt(self.args[1:], "c:df:hp", \
                              ["config-file=", "debug", "file=", "help",
                               "print"])
        except getopt.GetoptError, err:
            print >>sys.stderr, str(err)
            self.usage()
            sys.exit(2)

        # default values for command line args
        self.configfile = "mlogr.conf"
        mlogr.DEBUG = False
        self.file = "mlogr.db"

        for o, a in opts:
            if o in ["-c", "--config-file"]:
                self.configfile = a
            elif o in ["-d", "--debug"]:
                mlogr.DEBUG = True
                print "Printing DEBUG information..."
            elif o in ["-f", "--file"]:
                self.file = a
            elif o in ["-h", "--help"]:
                mlogr.usage()
                sys.exit()
            elif o in ["-p", "--print-config"]:
                Config(self.configfile).print_config()
                sys.exit()


    def create_tables(self):
        """
        Create tables for logging data (tables defined in configuration).
        """
        for table in self.config.table_defs:
            if mlogr.DEBUG:
                print "DEBUG: Creating table", table

            # create sql syntax for table creation
            try:
                # every table row has id and unix timestamp
                create_table = r"""create table %s
                                        (id integer primary key,
                                         timestamp integer """ % table
                # create placeholder values for every column
                for column, type in self.config.table_defs[table].iteritems():
                    create_table += ", %s %s" % (column, type)
                create_table += ")"

                if mlogr.DEBUG:
                    print "DEBUG:", create_table
                    print "DEBUG:", self.config.table_defs[table]

                with self.conn:
                    self.conn.execute(create_table)

                print "Created log table '%s'..." % table
            except sqlite3.OperationalError, e:
                table_exists = "table %s already exists" % table

                if unicode(e) == table_exists:
                    print "Log table '%s' exists..." % table
                else:
                    print >>sys.stderr, e


    def input_loop(self):
        """
        Loop for user input.
        """
        # dictionary for storing all responses
        self.responses = {}

        # read input for fields
        for table in self.config.tables:
            self.responses[table] = {}

            print "\nGive input for %s..." % table
            print "Empty input skips value.\n"

            for column, type in self.config.table_defs[table].iteritems():
                next_column = False # flag for continuing to next value
                while not next_column:
                    try:
                        sys.stdout.write("%s (%s): " % (column, type))
                        response = sys.stdin.readline().rstrip("\r\n")

                        # if response is empty skip value
                        if response == "":
                            next_column = True
                            continue

                        self.check_response(column, type, response)

                        self.responses[table][column] = response
                        next_column = True
                    except exception.BadResponse, e:
                        print >>sys.stderr, e


    def check_response(self, column, column_type, response):
        """
        Check that user input is valid.
        """
        # check that input conforms to type
        try:
            if column_type == "boolean":
                bool(response)
            elif column_type == "integer":
                int(response)
            elif column_type == "real":
                float(response)
        except ValueError:
            raise exception.BadResponse(column, column_type, response)


    def validate_input(self):
        """
        Let the user validate given input.
        """
        if mlogr.DEBUG:
            print "DEBUG:", self.responses

        done = 0
        while done < len(self.config.tables):
            for table in self.responses:
                print "\nGiven input for", table

                # build correcting menu with values, zipped with number
                i = 0
                menu = []
                for column, type in self.config.table_defs[table].iteritems():
                    menu.append((column, type))

                    try:
                        menuitem = \
                            "%d) %s = %s" \
                            % (i, column, \
                               self.responses[table][column])
                    except KeyError:
                        menuitem = \
                            "%d) %s =" % (i, column)

                    print menuitem

                    i += 1

                inputmsg = \
                    "Enter number to change given input or enter to accept: "
                sys.stdout.write(inputmsg)
                correct = sys.stdin.readline().rstrip("\r\n")

                # continue if everything was ok (user hit enter)
                if correct == "":
                    done += 1
                    continue

                # correct value otherwise
                print "Correct value"
                corr_column, corr_type = menu[int(correct)]

                # ask user to give correcting update
                corrected = False
                while not corrected:
                    try:
                        correctmsg = "%s (%s) [%s]: " \
                                     % (corr_column, corr_type, \
                                        self.responses[table][corr_column])
                    except KeyError:
                        correctmsg = "%s (%s) []: " % (corr_column, corr_type)

                    try:
                        print "Empty input uses already given value"
                        sys.stdout.write(correctmsg)
                        correct_value = sys.stdin.readline().rstrip("\r\n")

                        self.check_response(corr_column, corr_type, \
                                            correct_value)

                        self.responses[table][corr_column] = correct_value
                        corrected = True
                    except exception.BadResponse, e:
                        print >>sys.stderr, e


    def write_to_db(self):
        """
        Write user input to database.
        """
        timestamp = datetime.datetime.now().strftime("%s")
        with self.conn:
            for table in self.config.table_defs:
                # always insert timestamp
                insert_sql = "insert into %s (timestamp, " % table
                preparation = "(?, "
                values = [timestamp]

                for column, type in self.config.table_defs[table].iteritems():
                    insert_sql += column + ", "
                    preparation += "?, "

                    # prepare values to be inserted
                    try:
                        # transform values from user input strings
                        processed_value = \
                            self.transform(self.responses[table][column], type)

                        values.append(processed_value)
                    except KeyError:
                        # pad prepared values with null for empty user input
                        values.append(None)

                # remove last comma and add parenthesis
                insert_sql = insert_sql[0:-2] + ") values "
                preparation = preparation[0:-2] + ")"

                # add preparation to sql insert statement
                insert_sql += preparation
                values = tuple(values)

                if mlogr.DEBUG:
                    print "DEBUG:", insert_sql
                    print "DEBUG:\t\t", values

                with self.conn:
                    self.conn.execute(insert_sql, values)


    def run_posthook(self):
        """
        Run post hooks.
        """
        # bail if no post-hook exists
        if not os.path.isfile(os.getwcd() + "/hooks/post-hook.py"):
            return None

        try:
            print "Running post-hook..."
            __import__("hooks.post-hook")
        except ImportError:
            print >>sys.stderr, "Error while running post-hook..."


    def transform(self, data, type):
        if type == "boolean":
            return bool(data)
        elif type == "integer":
            return int(data)
        elif type == "real":
            return float(data)
        elif type == "text":
            return str(data)
        else:
            raise exception.InvalidType(type, data)
