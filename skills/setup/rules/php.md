---
paths:
  - "**/*.php"
---
# PHP
<!-- Clio starter — /clio:setup step 4. Verify every line against this repo, delete lines that
     don't hold here, delete the whole file if the repo has no PHP. Keep it under 20 lines. -->

- `declare(strict_types=1);` is the first statement of every new file; follow the repo where existing files differ.
- Never edit `vendor/`. Dependency change → `composer.json`, then `composer update <pkg>`; commit `composer.lock`.
- New class in a PSR-4 namespace that won't autoload → `composer dump-autoload`, never a manual `require`.
- Formatter: `vendor/bin/pint` (Laravel) or `vendor/bin/php-cs-fixer fix` — whichever `composer.json` lists. Wire it as the step-6 PostToolUse hook.
- Tests: `vendor/bin/phpunit` (Laravel: `php artisan test`). Every bug fix ships with the test that reproduced it.
- Money: integer minor units or `brick/money`; never float arithmetic on an amount.
- Laravel: an applied migration is frozen — add a new one, never edit it. Generated: `bootstrap/cache/`, `public/build/` (source: `resources/`).
- Zend Framework / Laminas: one module per bounded area under `module/<Name>/`; routes, services and controllers register in `module/<Name>/config/module.config.php`, `Module.php` holds bootstrap only. Zend namespaces were renamed to Laminas in 2020 — read `composer.json` for which one this repo uses before writing any import.
