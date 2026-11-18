from __future__ import annotations

from typing import Any

RU: dict[str, str] = {
    "prompt": "сообщение или /help   ·   enter — отправить",
    "ui.ready": "AcidCode готов.",
    "ui.hint": "Спроси про репозиторий или опиши правку · /help — команды",
    "ui.files": "ФАЙЛЫ",
    "ui.preview_missing": "файл не найден или вне рабочей папки",
    "ui.truncated": "… ещё {count} строк",
    "ui.shell_run": "выполняю…",
    "ui.search_run": "ищу…",
    "ui.tokens": "токенов",
    "ui.limit": "лимит",
    "banner.provider": "провайдер",
    "banner.model": "модель",
    "banner.folder": "папка",
    "banner.budget": "бюджет",
    "banner.hint": "/key <ключ> · /providers · /help",
    "banner.rating": "/models — рейтинг и цены",
    "tier.top": "ТОП",
    "tier.mid": "СРЕДНЯК",
    "tier.bad": "КАЛ",
    "price.free": "бесплатно",
    "price.paid": "платно",
    "models.title": "рейтинг моделей · бюджет {budget} на модель",
    "models.key": "ключ",
    "models.hint": "переключение: /switch <номер> · следующая: /switch next · фильтры: /models free|paid|top|mid|bad",
    "models.bad_filter": "фильтр: free | paid | top | mid | bad (или бесплатно/платно/топ/среднее/кал)",
    "usage.title": "расход · бюджет {budget} на модель",
    "usage.empty": "расход пуст · бюджет {budget} на модель",
    "usage.requests": "запросов",
    "usage.hint": "сброс: /usage reset · или /usage reset <provider>",
    "status.provider": "провайдер",
    "status.model": "модель",
    "status.budget": "бюджет",
    "status.key_yes": "да",
    "status.key_no": "нет (можно из env)",
    "status.key": "ключ в конфиге",
    "status.thinking": "thinking",
    "status.folder": "папка",
    "status.messages": "сообщений в контексте",
    "status.config": "конфиг",
    "status.na": "н/д",
    "cmd.cleared": "экран очищен",
    "cmd.new": "новый чат",
    "cmd.unknown": "неизвестная команда: {cmd} · /help",
    "switch.need": "нужно: /switch 3 (номер из /models) или /switch next",
    "switch.none": "следующей модели с ключом и остатком нет",
    "switch.bad_number": "нужен номер или next",
    "switch.not_found": "такого номера нет — смотри /models",
    "switch.no_key": "нет ключа для {provider}. вставь /key <ключ> после /provider {provider}",
    "switch.done": "переключился на {provider}/{model}",
    "provider.need": "нужно имя: /provider groq",
    "provider.unknown": "нет такого: {name}",
    "provider.done": "провайдер → {name}",
    "key.need": "нужен ключ: /key sk-...",
    "key.saved": "ключ сохранён для {provider} ({count} символов)",
    "model.current": "текущая: {model}",
    "model.default": "по умолчанию",
    "model.default_line": "дефолт: {model}",
    "model.done": "модель → {model}",
    "system.current": "текущий: {text}",
    "system.done": "системный промпт обновлён",
    "reasoning.current": "текущий уровень: {level}",
    "reasoning.options": "варианты: off | low | high | max (только deepseek)",
    "reasoning.bad": "нужно: off, low, high или max",
    "reasoning.done": "thinking → {level}",
    "save.done": "сохранено → {path}",
    "load.need": "нужно имя: /load last",
    "load.none": "нет сессии: {name}",
    "load.done": "загружено {count} сообщений из {name}",
    "sessions.empty": "(пусто)",
    "usage.reset_done": "бюджет сброшен: записей {count}",
    "turn.budget_switch": "↷ бюджет {provider}/{model} исчерпан ({spent}/{budget}) → переключился на {next_provider}/{next_model}",
    "turn.budget_none": "✖ бюджет исчерпан: {provider}/{model} ({spent}/{budget}), других моделей с ключом и остатком нет",
    "turn.billing": "↷ {provider}/{model}: баланс пуст → бесплатный pollinations/openai",
    "turn.overloaded": "↷ {provider}/{model} перегружена → пробую {next_provider}/{next_model}",
    "turn.restore": "↷ все замены заняты → возвращаю {provider}/{model}",
    "identity": "AcidCode · модель {model} · провайдер {provider}",
    "lang.current": "язык: {lang} · /lang ru|en",
    "lang.done": "язык → {lang}",
    "lang.bad": "нужно: ru или en",
    "theme.current": "тема: {name}",
    "theme.done": "тема → {name}",
    "theme.bad": "нет такой темы: {name} · /theme покажет список",
    "theme.label.acid": "зелёная",
    "theme.label.amber": "янтарная",
    "theme.label.ice": "лёд",
    "theme.label.violet": "фиолет",
    "theme.label.mono": "моно",
    "key.quit": "выход",
    "key.new": "новый",
    "key.save": "сохранить",
    "key.help": "справка",
    "providers.title": "провайдеры (ключ → где взять):",
    "providers.docs": "ключ",
    "providers.env": "env",
    "update.checking": "проверяю обновления…",
    "update.no_source": "нет источника. задай update_url в config.json или: /update <папка|URL>",
    "update.none": "обновлений нет · версия {version}",
    "update.ready": "↻ есть версия {version} (сейчас {current}) · /update установит",
    "update.done": "✓ обновлено до {version}: файлов {count} · перезапусти AcidCode",
    "update.fail": "✖ обновление: {error}",
    "update.source_saved": "источник сохранён: {source}",
    "tag": "◇ {provider}/{model}",
}

EN: dict[str, str] = {
    "prompt": "message or /help   ·   enter — send",
    "ui.ready": "AcidCode is ready.",
    "ui.hint": "Ask about the repo or describe a change · /help — commands",
    "ui.files": "FILES",
    "ui.preview_missing": "file not found or outside the workspace",
    "ui.truncated": "… {count} more lines",
    "ui.shell_run": "running…",
    "ui.search_run": "searching…",
    "ui.tokens": "tokens",
    "ui.limit": "limit",
    "banner.provider": "provider",
    "banner.model": "model",
    "banner.folder": "folder",
    "banner.budget": "budget",
    "banner.hint": "/key <key> · /providers · /help",
    "banner.rating": "/models — ranking and prices",
    "tier.top": "TOP",
    "tier.mid": "AVERAGE",
    "tier.bad": "TRASH",
    "price.free": "free",
    "price.paid": "paid",
    "models.title": "model ranking · budget {budget} per model",
    "models.key": "key",
    "models.hint": "switch: /switch <n> · next: /switch next · filters: /models free|paid|top|mid|bad",
    "usage.title": "usage · budget {budget} per model",
    "usage.empty": "no usage yet · budget {budget} per model",
    "usage.requests": "requests",
    "usage.hint": "reset: /usage reset · or /usage reset <provider>",
    "status.provider": "provider",
    "status.model": "model",
    "status.budget": "budget",
    "status.key_yes": "yes",
    "status.key_no": "no (env still works)",
    "status.key": "key in config",
    "status.thinking": "thinking",
    "status.folder": "folder",
    "status.messages": "messages in context",
    "status.config": "config",
    "status.na": "n/a",
    "cmd.cleared": "screen cleared",
    "cmd.new": "new chat",
    "cmd.unknown": "unknown command: {cmd} · /help",
    "switch.need": "usage: /switch 3 (number from /models) or /switch next",
    "switch.none": "no next model with a key and budget left",
    "switch.bad_number": "need a number or next",
    "switch.not_found": "no such number — check /models",
    "switch.no_key": "no key for {provider}. run /provider {provider} then /key <key>",
    "switch.done": "switched to {provider}/{model}",
    "provider.need": "need a name: /provider groq",
    "provider.unknown": "no such provider: {name}",
    "provider.done": "provider → {name}",
    "key.need": "need a key: /key sk-...",
    "key.saved": "key saved for {provider} ({count} chars)",
    "model.current": "current: {model}",
    "model.default": "default",
    "model.default_line": "default: {model}",
    "model.done": "model → {model}",
    "system.current": "current: {text}",
    "system.done": "system prompt updated",
    "reasoning.current": "current level: {level}",
    "reasoning.options": "options: off | low | high | max (deepseek only)",
    "reasoning.bad": "need: off, low, high or max",
    "reasoning.done": "thinking → {level}",
    "save.done": "saved → {path}",
    "load.need": "need a name: /load last",
    "load.none": "no session: {name}",
    "load.done": "loaded {count} messages from {name}",
    "sessions.empty": "(empty)",
    "usage.reset_done": "budget reset: {count} entries",
    "turn.budget_switch": "↷ budget {provider}/{model} exhausted ({spent}/{budget}) → switched to {next_provider}/{next_model}",
    "turn.budget_none": "✖ budget exhausted: {provider}/{model} ({spent}/{budget}), no other model with a key and budget left",
    "turn.billing": "↷ {provider}/{model}: no balance → free pollinations/openai",
    "turn.overloaded": "↷ {provider}/{model} overloaded → trying {next_provider}/{next_model}",
    "turn.restore": "↷ all replacements busy → back to {provider}/{model}",
    "identity": "AcidCode · model {model} · provider {provider}",
    "lang.current": "language: {lang} · /lang ru|en",
    "lang.done": "language → {lang}",
    "lang.bad": "need: ru or en",
    "theme.current": "theme: {name}",
    "theme.done": "theme → {name}",
    "theme.bad": "no such theme: {name} · /theme lists them",
    "theme.label.acid": "green",
    "theme.label.amber": "amber",
    "theme.label.ice": "ice",
    "theme.label.violet": "violet",
    "theme.label.mono": "mono",
    "key.quit": "quit",
    "key.new": "new",
    "key.save": "save",
    "key.help": "help",
    "providers.title": "providers (key → where to get):",
    "providers.docs": "key",
    "providers.env": "env",
    "update.checking": "checking for updates…",
    "update.no_source": "no source. set update_url in config.json or: /update <folder|URL>",
    "update.none": "up to date · version {version}",
    "update.ready": "↻ version {version} available (current {current}) · /update installs it",
    "update.done": "✓ updated to {version}: {count} files · restart AcidCode",
    "update.fail": "✖ update: {error}",
    "update.source_saved": "source saved: {source}",
    "tag": "◇ {provider}/{model}",
}

LANGS: dict[str, dict[str, str]] = {"ru": RU, "en": EN}

HELP_RU = """команды
  /help                эта справка
  /provider <имя>      сменить провайдера (список: /providers)
  /providers           все провайдеры и ключи
  /key <ключ>          сохранить ключ для текущего провайдера
  /model <имя>         выбрать модель
  /models [фильтр]     рейтинг, цены и расход: free|paid|top|mid|bad
  /switch <n|next>     перейти на модель по номеру или следующую
  /usage [reset ...]   расход по моделям, сброс бюджета
  /lang ru|en          язык интерфейса
  /theme [имя]         цвета: acid | amber | ice | violet | mono
  /update [check|путь] обновиться из папки или URL (check — только проверить)
  /system <текст>      системный промпт
  /reasoning <ур>      thinking у deepseek: off | low | high | max
  /status              что сейчас включено
  /new                 новый чат
  /save [имя]          сохранить сессию
  /load <имя>          загрузить сессию
  /sessions            список сохранённых
  /clear               очистить экран
  /exit                выйти

клавиши
  enter — отправить · ctrl+c — выход · ctrl+n — новый чат
  ctrl+s — сохранить · f1 — справка"""

HELP_EN = """commands
  /help                this help
  /provider <name>     switch provider (list: /providers)
  /providers           all providers and key pages
  /key <key>           save key for current provider
  /model <name>        choose model
  /models [filter]     ranking, prices, usage: free|paid|top|mid|bad
  /switch <n|next>     switch by number or to the next one
  /usage [reset ...]   usage per model, reset budget
  /lang ru|en          interface language
  /theme [name]        colors: acid | amber | ice | violet | mono
  /update [check|path] update from folder or URL (check — check only)
  /system <text>       system prompt
  /reasoning <level>   deepseek thinking: off | low | high | max
  /status              current state
  /new                 new chat
  /save [name]         save session
  /load <name>         load session
  /sessions            saved sessions
  /clear               clear screen
  /exit                quit

keys
  enter — send · ctrl+c — quit · ctrl+n — new chat
  ctrl+s — save · f1 — help"""

HELP_TEXTS = {"ru": HELP_RU, "en": HELP_EN}


def t(locale: str, key: str, **kwargs: Any) -> str:
    table = LANGS.get(locale, RU)
    template = table.get(key) or RU.get(key) or key
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError):
        return template


def help_text(lang: str) -> str:
    return HELP_TEXTS.get(lang, HELP_RU)


def tier_label(lang: str, tier: str) -> str:
    return t(lang, f"tier.{tier}")


FILTER_ALIASES: dict[str, str] = {
    "free": "free",
    "бесплатно": "free",
    "бесплатные": "free",
    "бесплатный": "free",
    "paid": "paid",
    "платно": "paid",
    "платные": "paid",
    "платный": "paid",
    "top": "top",
    "топ": "top",
    "лучшие": "top",
    "mid": "mid",
    "average": "mid",
    "среднее": "mid",
    "средние": "mid",
    "средняк": "mid",
    "bad": "bad",
    "плохое": "bad",
    "плохие": "bad",
    "кал": "bad",
}


def normalize_filter(text: str) -> str:
    """Приводит free/paid/top/mid/bad и русские синонимы к ключу фильтра."""
    return FILTER_ALIASES.get(text.strip().lower(), "")
