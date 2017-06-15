from sys import version_info

if version_info[0] == 2:
    from mock import Mock
else:
    from unittest.mock import Mock


class NamedMock(Mock):

    @property
    def name(self):
        return self.real_name