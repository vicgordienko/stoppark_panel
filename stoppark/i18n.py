# -*- coding: utf-8 -*-

import gettext

#  The translation files will be under
#  @LOCALE_DIR@/@LANGUAGE@/LC_MESSAGES/@APP_NAME@.mo
APP_NAME = "stoppark"
LOCALE_DIR = 'i18n'

# Now we need to choose the language. We will provide a list, and gettext
# will use the first translation available in the list
DEFAULT_LANGUAGES = ['ru_RU']

gettext.install(True, localedir=None, unicode=1)

#print gettext.find(APP_NAME, LOCALE_DIR, languages=DEFAULT_LANGUAGES)
#print gettext.bindtextdomain(APP_NAME, LOCALE_DIR)
#print gettext.textdomain(APP_NAME)
#gettext.bind_textdomain_codeset(APP_NAME, "UTF-8")
language = gettext.translation(APP_NAME, LOCALE_DIR, languages=DEFAULT_LANGUAGES)
language.install(unicode=1)