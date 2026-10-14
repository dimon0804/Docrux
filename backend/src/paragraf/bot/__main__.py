"""Запуск: python -m paragraf.bot"""

import sys

from paragraf.bot.app import BotTokenMissing, main

try:
    main()
except BotTokenMissing as exc:
    print(exc, file=sys.stderr)
    sys.exit(2)
except KeyboardInterrupt:
    pass
