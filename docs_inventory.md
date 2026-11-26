# Інвентар пакета документації (РГР)

## Включено
- docs/architecture.md
- docs/user_guide.md
- docs/decisions.md
- docs/coding_convention.md
- docs/api/openapi.yaml, docs/api/rest_api.html
- docs/api/conf.py, docs/api/*.rst
- docs/api/html/*.html (Sphinx, лише верхній рівень)

## Виключено і чому
- SRS, spec/ (крім openapi.yaml): первинні вимоги, мета експерименту їх не мати.
- docs/api/_build/_modules: повний вихідний код src/ (viewcode).
- docs/api/_build/_sources, .doctrees, _static: службові файли Sphinx.
- impl_plan.md, test_matrix.md, test_open_questions.md: процесні документи, що переказують SRS або розкривають тести.
- glossary_check.md, audit_report.md, convention_report.md, refactor_report.md, matrix_notes.md: звіти з даними про src/tests.
- verification_*.md, validation_final.md: результати перевірок, а не документація.

## Відомі посилання на відсутні документи
- architecture.md: рядки 8, 173, 178, 198 (SRS), 43, 197-199 (src/, tests/, spec/; перевірити зміст).
- coding_convention.md: рядки 4, 24 (SRS), 33-55 (шляхи src/, tests/).
- decisions.md: рядки 5, 11, 14-19, 21 (SRS, spec/, tests/conftest.py).

Ці посилання не редагувались. Їх вплив на реалізацію описується в GAP-LOG.md і GAP-REPORT.md.
