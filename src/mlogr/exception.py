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

class MlogrException(Exception):
    """
    Base exception for mlogr exceptions.
    """
    def __init__(self, value):
        self.value = value

class MlogrConfigException(MlogrException):
    """
    Base class for mlogr configuration exceptions.
    """

class NoConfigFile(MlogrConfigException):
    def __str__(self):
        return "Supplied config file '%s' does not exist" % self.value

class NoDbFile(MlogrConfigException):
    def __str__(self):
        return "Supplied database file '%s' does not exist" % self.value

class DuplicateTable(MlogrException):
    pass

class BadTableName(MlogrException):
    def __str__(self):
        return "Table '%s' hase a bad name" % self.value

class TableMissingDef(MlogrException):
    def __str__(self):
        return "Table '%s' is not defined in the config file." % self.value

class BadColumnName(MlogrException):
    def __str__(self):
        return "Column '%s' has a invalid name." % self.value

class BadColumnType(MlogrException):
    """
    Bad definition of column in configuration of table definition.
    """
    def __init__(self, name, type):
        self.name = name
        self.type = type

    def __str__(self):
        return "Column '%s' has bad type definition '%s'." \
                % (self.name, self.type)

class BadResponse(MlogrException):
    """
    Bad response.
    """
    def __init__(self, column, type, value):
        self.column = column
        self.type = type
        self.value = value

    def __str__(self):
        return "Bad response '%s' for column '%s' of type '%s'." \
               % (self.column, self.type, self.value)

class InvalidType(MlogrException):
    """
    Invalid type for input value.
    """
    def __init__(self, type, value):
        self.type = type
        self.value = value

    def __str__(self):
        return "Invalid type '%s' for value '%s'." % (self.type, self.value)
