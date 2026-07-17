# Magento 2 Framework Rules

Read WITH `rules/php.md`. Magento's extension architecture IS the ladder —
core is never edited; every change routes through a sanctioned seam. The
codebase is huge: assume it exists before writing it.

## The platform sweep (before ANY new code)

`codemap.py vendor <term>` across `magento/framework` and `magento/module-*`:
service contracts (`Api\*Interface` + repositories), `Magento\Framework`
utilities (Serializer, HTTP client, filesystem, validation, math/currency),
existing view models, the module that already owns the domain. Search
`module-<domain>` before inventing a parallel concept.

## Extension seams (strict preference order)

1. Configuration: system.xml/admin config, di.xml arguments — rung 1.
2. **Plugin (interceptor)** on a public method — before/after/around; the
   idiomatic rung 2–3. Prefer `after` (least invasive); `around` only with a
   stated reason (it can swallow the call chain).
3. Observer on an existing event — side effects without touching flow.
4. **View model** for template logic — never block-class overrides for data.
5. Extension attributes on service contracts — additive data, Zeroth Law
   aligned.
6. di.xml `preference` (class rewrite) — the LAST resort (rung 7-equivalent);
   one preference per class repo-wide, so you may be stealing the slot from
   the next module. Justify in the gate record.
7. New module (rung 8) only for a genuinely new domain — registration.php +
   module.xml + sequence declared, not a grab-bag "Custom" module.

## Anti-patterns to refuse

- `Helper\Data` grab-bags (Magento's own worst habit — don't copy it).
- ObjectManager direct use outside factories/proxies — constructor DI always.
- Around-plugins that reimplement the intercepted method (C9 in disguise).
- A preference where a plugin would do; template overrides for logic.

## Dynamic-reference checklist ADDITIONS (on top of php.md)

- XML is a reference graph: di.xml (plugins, preferences, virtual types,
  argument class names), events.xml, webapi.xml routes, layout XML (blocks +
  viewModel arguments), ui_component XML, system.xml source/backend models,
  crontab.xml jobs, email templates, widget.xml, indexer/mview.xml.
- `generated/` code: Factories/Proxies/Interceptors are generated FROM your
  classes — a class with zero source refs may be constructed via its
  generated Factory string-wise.
- Virtual types exist only in di.xml — invisible to any code scan.
- setup/patch classes and `setup_module` versions; disabled-module state
  (a module in app/etc/config.php with `0` is dormant, not dead).
- Admin ACL (acl.xml), menu.xml, and route ids referenced by string.
- Zeroth Law: service contracts (Api interfaces), REST/SOAP routes, and
  extension attributes are public surface — additive only, always.

## When planning / verifying

Plan tasks name the seam and target ("after-plugin on
`QuoteManagement::placeOrder`", "view model for X template") — never "edit
core", rarely "preference". Verify: XML references resolve (a renamed class
breaks di.xml silently until runtime), `setup:di:compile` passes, no new
Helper grab-bag, and every around-plugin justifies why after/before couldn't.

## Templates (.phtml)

- Templates are now indexed: a view-model/block method "unused" in PHP but
  called in a .phtml shows real refs in the map — trust the map, then still
  grep layout XML before any deletion.
- Logic in templates is a smell: it belongs in the view model (rung 4-5), not
  `<?php` blocks in .phtml. A template needing new data = a view-model method.
- Overriding a template in your theme copies the WHOLE file (Magento's
  mechanism — unavoidable), so keep core templates' overrides minimal and
  diff-reviewed against the original at upgrade time; never fork a template
  to change what a plugin/view model could.
- `codemap.py clones` across app/design themes finds the copied-template
  drift that accumulates over upgrades.
