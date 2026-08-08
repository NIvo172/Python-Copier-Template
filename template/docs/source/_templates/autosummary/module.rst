{{ fullname | escape | underline }}

.. automodule:: {{ fullname }}

{% if attributes %}
Module Attributes
-----------------

.. autosummary::
   :toctree:
{% for item in attributes %}
   {{ item }}
{% endfor %}
{% endif %}
{% if functions %}
Functions
---------

.. autosummary::
   :toctree:
{% for item in functions %}
   {{ item }}
{% endfor %}
{% endif %}
{% if classes %}
Classes
-------

.. autosummary::
   :toctree:
{% for item in classes %}
   {{ item }}
{% endfor %}
{% endif %}
{% if exceptions %}
Exceptions
----------

.. autosummary::
   :toctree:
{% for item in exceptions %}
   {{ item }}
{% endfor %}
{% endif %}
{% if modules %}
Modules
-------

.. autosummary::
   :toctree:
   :recursive:
{% for item in modules %}
   {{ item }}
{% endfor %}
{% endif %}
