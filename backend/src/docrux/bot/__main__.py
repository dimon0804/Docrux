"""Запуск: python -m docrux.bot"""

import sys

from docrux.bot.app import BotTokenMissing, main

try:
    main()
except BotTokenMissing as exc:
    print(exc, file=sys.stderr)
    sys.exit(2)
except KeyboardInterrupt:
    pass
