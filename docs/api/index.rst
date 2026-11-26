AutoBook SDD — довідник API та коду
===================================

Цей довідник створюється з документації в коді. Опис архітектури, моделі
даних, потоків і відомих обмежень наведено в `документі архітектури
<../architecture.md>`_.

.. toctree::
   :maxdepth: 2
   :caption: Пакети

   models
   src.api
   src.services
   src.repositories
   src.core

Збірка в PowerShell з кореня проєкту:

.. code-block:: powershell

   sphinx-build -W -b html docs\api docs\api\_build
