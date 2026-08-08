---
title: ADR-003 — ЕИС RSS and TLS boundary
type: decision
status: accepted
updated: 2026-08-08
---

# ADR-003: официальный RSS для актуальных ЕИС notices

## Контекст

MVP должен регулярно получать актуальные закупки РФ, но не выгружать ЕИС целиком и не строить скрытый
HTML scraper. Публичная страница расширенного поиска предоставляет RSS-подписку, а TLS endpoint
`*.zakupki.gov.ru` использует российскую цепочку, для которой одного root CA недостаточно: сервер не
передаёт issuing CA в подходящем для стандартного клиента виде. Ручной XML/ZIP import уже нужен для
ограниченных historical/results packages и не должен исчезать.

## Решение

- Live adapter читает только официальный HTTPS RSS endpoint расширенного поиска; endpoint является
  константой кода и не принимается от пользователя.
- MVP запрашивает только 44-ФЗ, первую страницу, сортировку по update date, publication interval не
  более 31 дня и page size `10/20/50`; фактически сохраняется не более requested limit.
- RSS 2.0 ограничен 2 MiB и 50 items. DTD/ENTITY, invalid XML/schema, duplicate/invalid registry number,
  item URL вне `https://zakupki.gov.ru` и неожиданный media type завершают run явной ошибкой.
- Валидный channel без items означает наблюдаемый успешный `0 records`, а не сбой или скрытый unknown.
- Каждый response сохраняется content-addressed в raw storage; request bounds, run, SHA-256 и source URL
  связываются с canonical SCD2 record. Replay того же canonical payload не создаёт новую version.
- TLS context загружает проверенные root и issuing CA Минцифры. Отключение проверки сертификата не
  допускается; fingerprints защищены тестом, expiry — документированной процедурой ротации.
- Manual XML/ZIP upload остаётся отдельным bounded port для исторических извещений/результатов.

## Последствия

ЕИС становится регулярным live-источником актуальных notices без full export и scraping. RSS не обещает
полноту 223-ФЗ, CPV, deadline, supplier или contract outcome; отсутствующие факты остаются `unknown` и
могут быть дополнены только evidence-backed package/detail adapter. Изменение RSS-полей или TLS chain
ломает contract/certificate tests громко, после чего оператор обновляет один source adapter/CA asset,
а не downstream canonical, matcher или marts.
