{{ fullname | escape | underline }}

.. currentmodule:: {{ module }}

.. autoclass:: {{ objname }}
   :members:
   :inherited-members:
   :show-inheritance:
   :special-members: __init__

{% if methods %}
Methods
-------

.. autosummary::
{% for item in methods %}
   ~{{ name }}.{{ item }}
{% endfor %}
{% endif %}
{% if attributes %}
Attributes
----------

.. autosummary::
{% for item in attributes %}
   ~{{ name }}.{{ item }}
{% endfor %}
{% endif %}
