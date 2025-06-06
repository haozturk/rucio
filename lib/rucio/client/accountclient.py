# Copyright European Organization for Nuclear Research (CERN) since 2012
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from json import dumps
from typing import TYPE_CHECKING, Any, Optional
from urllib.parse import quote_plus

from requests.status_codes import codes

from rucio.client.baseclient import BaseClient, choice
from rucio.common.utils import build_url

if TYPE_CHECKING:
    from collections.abc import Iterator


class AccountClient(BaseClient):

    """Account client class for working with rucio accounts"""

    ACCOUNTS_BASEURL = 'accounts'

    def add_account(self, account: str, type_: str, email: str) -> bool:
        """
        Sends the request to create a new account.

        Parameters
        ----------
        account :
            The name of the account.
        type_ :
            The account type.
        email :
            The Email address associated with the account.

        Returns
        -------

            True if account was created successfully else False.

        Raises
        ------
        Duplicate
            If account already exists.
        """

        data = dumps({'type': type_, 'email': email})
        path = '/'.join([self.ACCOUNTS_BASEURL, account])
        url = build_url(choice(self.list_hosts), path=path)

        res = self._send_request(url, type_='POST', data=data)
        if res.status_code == codes.created:
            return True
        exc_cls, exc_msg = self._get_exception(headers=res.headers, status_code=res.status_code, data=res.content)
        raise exc_cls(exc_msg)

    def delete_account(self, account: str) -> bool:
        """
        Send the request to disable an account.

        Parameters
        ----------
        account :
            The name of the account.

        Returns
        -------

            True if account was disabled successfully. False otherwise.

        Raises
        ------
        AccountNotFound
            If account doesn't exist.
        """

        path = '/'.join([self.ACCOUNTS_BASEURL, account])
        url = build_url(choice(self.list_hosts), path=path)

        res = self._send_request(url, type_='DEL')

        if res.status_code == codes.ok:
            return True
        exc_cls, exc_msg = self._get_exception(headers=res.headers, status_code=res.status_code, data=res.content)
        raise exc_cls(exc_msg)

    def get_account(self, account: str) -> Optional[dict[str, Any]]:
        """
        Send the request to get information about a given account.

        Parameters
        ----------
        account :
            The name of the account.

        Returns
        -------

            A dictionary of attributes for the account. None if failure.

        Raises
        ------
        AccountNotFound
            If account doesn't exist.
        """

        path = '/'.join([self.ACCOUNTS_BASEURL, account])
        url = build_url(choice(self.list_hosts), path=path)

        res = self._send_request(url)
        if res.status_code == codes.ok:
            acc = self._load_json_data(res)
            return next(acc)
        exc_cls, exc_msg = self._get_exception(headers=res.headers, status_code=res.status_code, data=res.content)
        raise exc_cls(exc_msg)

    def update_account(self, account: str, key: str, value: Any) -> bool:
        """
        Update a property of an account.

        Parameters
        ----------
        account :
            Name of the account.
        key :
            Account property like status.
        value :
            Property value.

        Returns
        -------

            True if successful.

        Raises
        ------
        Exception
            If update fails.
        """
        data = dumps({key: value})
        path = '/'.join([self.ACCOUNTS_BASEURL, account])
        url = build_url(choice(self.list_hosts), path=path)

        res = self._send_request(url, type_='PUT', data=data)

        if res.status_code == codes.ok:
            return True
        else:
            exc_cls, exc_msg = self._get_exception(headers=res.headers, status_code=res.status_code, data=res.content)
            raise exc_cls(exc_msg)

    def list_accounts(
            self,
            account_type: Optional[str] = None,
            identity: Optional[str] = None,
            filters: Optional[dict[str, Any]] = None
    ) -> "Iterator[dict[str, Any]]":
        """
        Send the request to list all rucio accounts.

        Parameters
        ----------
        account_type :
            The account type.
        identity :
            The identity key name. For example x509 DN, or a username.
        filters :
            A dictionary key:account attribute to use for the filtering.

        Returns
        -------

            An iterator of dictionaries containing account information.

        Raises
        ------
        AccountNotFound
            If account doesn't exist.
        """
        path = '/'.join([self.ACCOUNTS_BASEURL])
        url = build_url(choice(self.list_hosts), path=path)
        params = {}
        if account_type:
            params['account_type'] = account_type
        if identity:
            params['identity'] = identity
        if filters:
            for key in filters:
                params[key] = filters[key]

        res = self._send_request(url, params=params)

        if res.status_code == codes.ok:
            accounts = self._load_json_data(res)
            return accounts
        else:
            exc_cls, exc_msg = self._get_exception(headers=res.headers, status_code=res.status_code, data=res.content)
            raise exc_cls(exc_msg)

    def whoami(self) -> Optional[dict[str, Any]]:
        """
        Get information about account whose token is used.

        Returns
        -------

            A dictionary of attributes for the account. None if failure.

        Raises
        ------
        AccountNotFound
            If account doesn't exist.
        """
        return self.get_account('whoami')

    def add_identity(
            self,
            account: str,
            identity: str,
            authtype: str,
            email: str,
            default: bool = False,
            password: Optional[str] = None
    ) -> bool:
        """
        Add a membership association between identity and account.

        Parameters
        ----------
        account :
            The account name.
        identity :
            The identity key name. For example x509 DN, or a username.
        authtype :
            The type of the authentication (x509, gss, userpass).
        email :
            The Email address associated with the identity.
        default :
            If True, the account should be used by default with the provided identity.
        password :
            Password if authtype is userpass.

        Returns
        -------

            True if successful.

        """

        data = dumps({'identity': identity, 'authtype': authtype, 'default': default, 'email': email, 'password': password})
        path = '/'.join([self.ACCOUNTS_BASEURL, account, 'identities'])

        url = build_url(choice(self.list_hosts), path=path)

        res = self._send_request(url, type_='POST', data=data)

        if res.status_code == codes.created:
            return True
        else:
            exc_cls, exc_msg = self._get_exception(headers=res.headers, status_code=res.status_code, data=res.content)
            raise exc_cls(exc_msg)

    def del_identity(
            self,
            account: str,
            identity: str,
            authtype: str
    ) -> bool:
        """
        Delete an identity's membership association with an account.

        Parameters
        ----------
        account :
            The account name.
        identity :
            The identity key name. For example x509 DN, or a username.
        authtype :
            The type of the authentication (x509, gss, userpass).

        Returns
        -------

            True if successful.
        """

        data = dumps({'identity': identity, 'authtype': authtype})
        path = '/'.join([self.ACCOUNTS_BASEURL, account, 'identities'])

        url = build_url(choice(self.list_hosts), path=path)

        res = self._send_request(url, type_='DEL', data=data)

        if res.status_code == codes.ok:
            return True
        else:
            exc_cls, exc_msg = self._get_exception(headers=res.headers, status_code=res.status_code, data=res.content)
            raise exc_cls(exc_msg)

    def list_identities(self, account: str) -> "Iterator[dict[str, Any]]":
        """
        List all identities on an account.

        Parameters
        ----------
        account :
            The account name.
        """
        path = '/'.join([self.ACCOUNTS_BASEURL, account, 'identities'])
        url = build_url(choice(self.list_hosts), path=path)
        res = self._send_request(url)
        if res.status_code == codes.ok:
            identities = self._load_json_data(res)
            return identities
        else:
            exc_cls, exc_msg = self._get_exception(headers=res.headers, status_code=res.status_code, data=res.content)
            raise exc_cls(exc_msg)

    def list_account_rules(self, account: str) -> "Iterator[dict[str, Any]]":
        """
        List the associated rules of an account.

        Parameters
        ----------
        account :
            The account name.

        """

        path = '/'.join([self.ACCOUNTS_BASEURL, account, 'rules'])
        url = build_url(choice(self.list_hosts), path=path)
        res = self._send_request(url, type_='GET')
        if res.status_code == codes.ok:
            return self._load_json_data(res)
        else:
            exc_cls, exc_msg = self._get_exception(headers=res.headers, status_code=res.status_code, data=res.content)
            raise exc_cls(exc_msg)

    def get_account_limits(self, account: str, rse_expression: str, locality: str) -> dict[str, Any]:
        """
        Return the correct account limits for the given locality.

        Parameters
        ----------
        account :
            The account name.
        rse_expression :
            Valid RSE expression.
        locality :
            The scope of the account limit. 'local' or 'global'.

        """

        if locality == 'local':
            return self.get_local_account_limit(account, rse_expression)
        elif locality == 'global':
            return self.get_global_account_limit(account, rse_expression)
        else:
            from rucio.common.exception import UnsupportedOperation
            raise UnsupportedOperation('The provided locality (%s) for the account limit was invalid' % locality)

    def get_global_account_limit(self, account: str, rse_expression: str) -> dict[str, Any]:
        """
        List the account limit for the specific RSE expression.

        Parameters
        ----------
        account :
            The account name.
        rse_expression :
            The rse expression.

        """

        path = '/'.join([self.ACCOUNTS_BASEURL, account, 'limits', 'global', quote_plus(rse_expression)])
        url = build_url(choice(self.list_hosts), path=path)
        res = self._send_request(url, type_='GET')
        if res.status_code == codes.ok:
            return next(self._load_json_data(res))
        exc_cls, exc_msg = self._get_exception(headers=res.headers, status_code=res.status_code, data=res.content)
        raise exc_cls(exc_msg)

    def get_global_account_limits(self, account: str) -> dict[str, Any]:
        """
        List all RSE expression limits of this account.

        Parameters
        ----------
        account :
            The account name.
        """

        path = '/'.join([self.ACCOUNTS_BASEURL, account, 'limits', 'global'])
        url = build_url(choice(self.list_hosts), path=path)
        res = self._send_request(url, type_='GET')
        if res.status_code == codes.ok:
            return next(self._load_json_data(res))
        exc_cls, exc_msg = self._get_exception(headers=res.headers, status_code=res.status_code, data=res.content)
        raise exc_cls(exc_msg)

    def get_local_account_limits(self, account: str) -> dict[str, Any]:
        """
        List the account rse limits of this account.

        Parameters
        ----------
        account :
            The account name.
        """

        path = '/'.join([self.ACCOUNTS_BASEURL, account, 'limits', 'local'])
        url = build_url(choice(self.list_hosts), path=path)
        res = self._send_request(url, type_='GET')
        if res.status_code == codes.ok:
            return next(self._load_json_data(res))
        exc_cls, exc_msg = self._get_exception(headers=res.headers, status_code=res.status_code, data=res.content)
        raise exc_cls(exc_msg)

    def get_local_account_limit(self, account: str, rse: str) -> dict[str, Any]:
        """
        List the account rse limits of this account for the specific rse.

        Parameters
        ----------
        account :
            The account name.
        rse :
            The rse name.
        """

        path = '/'.join([self.ACCOUNTS_BASEURL, account, 'limits', 'local', rse])
        url = build_url(choice(self.list_hosts), path=path)
        res = self._send_request(url, type_='GET')
        if res.status_code == codes.ok:
            return next(self._load_json_data(res))
        exc_cls, exc_msg = self._get_exception(headers=res.headers, status_code=res.status_code, data=res.content)
        raise exc_cls(exc_msg)

    def get_local_account_usage(self, account: str, rse: Optional[str] = None) -> "Iterator[dict[str, Any]]":
        """
        List the account usage for one or all rses of this account.

        Parameters
        ----------
        account :
            The account name.
        rse :
            The rse name.
        """
        if rse:
            path = '/'.join([self.ACCOUNTS_BASEURL, account, 'usage', 'local', rse])
        else:
            path = '/'.join([self.ACCOUNTS_BASEURL, account, 'usage', 'local'])
        url = build_url(choice(self.list_hosts), path=path)
        res = self._send_request(url, type_='GET')
        if res.status_code == codes.ok:
            return self._load_json_data(res)
        else:
            exc_cls, exc_msg = self._get_exception(headers=res.headers, status_code=res.status_code, data=res.content)
            raise exc_cls(exc_msg)

    def get_global_account_usage(self, account: str, rse_expression: Optional[str] = None) -> "Iterator[dict[str, Any]]":
        """
        List the account usage for one or all RSE expressions of this account.

        Parameters
        ----------
        account :
            The account name.
        rse_expression :
            The rse expression.
        """
        if rse_expression:
            path = '/'.join([self.ACCOUNTS_BASEURL, account, 'usage', 'global', quote_plus(rse_expression)])
        else:
            path = '/'.join([self.ACCOUNTS_BASEURL, account, 'usage', 'global'])
        url = build_url(choice(self.list_hosts), path=path)
        res = self._send_request(url, type_='GET')
        if res.status_code == codes.ok:
            return self._load_json_data(res)
        else:
            exc_cls, exc_msg = self._get_exception(headers=res.headers, status_code=res.status_code, data=res.content)
            raise exc_cls(exc_msg)

    def get_account_usage_history(self, account: str, rse: str) -> dict[str, Any]:
        """
        List the account usage history of this account on rse.

        Parameters
        ----------
        account :
            The account name.
        rse :
            The rse name.
        """
        path = '/'.join([self.ACCOUNTS_BASEURL, account, 'usage/history', rse])
        url = build_url(choice(self.list_hosts), path=path)
        res = self._send_request(url, type_='GET')
        if res.status_code == codes.ok:
            return next(self._load_json_data(res))
        else:
            exc_cls, exc_msg = self._get_exception(headers=res.headers, status_code=res.status_code, data=res.content)
            raise exc_cls(exc_msg)

    def list_account_attributes(self, account: str) -> "Iterator[dict[dict[str, Any], Any]]":
        """
        List the attributes for an account.

        Parameters
        ----------
        account :
            The account name.
        """
        path = '/'.join([self.ACCOUNTS_BASEURL, account, 'attr/'])
        url = build_url(choice(self.list_hosts), path=path)
        res = self._send_request(url, type_='GET')
        if res.status_code == codes.ok:
            return self._load_json_data(res)
        else:
            exc_cls, exc_msg = self._get_exception(headers=res.headers, status_code=res.status_code, data=res.content)
            raise exc_cls(exc_msg)

    def add_account_attribute(self, account: str, key: str, value: Any) -> bool:
        """
        Add an attribute to an account.

        Parameters
        ----------
        account :
            The account name.
        key :
            The attribute key.
        value :
            The attribute value.
        """

        data = dumps({'key': key, 'value': value})
        path = '/'.join([self.ACCOUNTS_BASEURL, account, 'attr', key])
        url = build_url(choice(self.list_hosts), path=path)
        res = self._send_request(url, type_='POST', data=data)
        if res.status_code == codes.created:
            return True
        else:
            exc_cls, exc_msg = self._get_exception(headers=res.headers, status_code=res.status_code, data=res.content)
            raise exc_cls(exc_msg)

    def delete_account_attribute(self, account: str, key: str) -> bool:
        """
        Delete an attribute for an account.

        Parameters
        ----------
        account :
            The account name.
        key :
            The attribute key.
        """

        path = '/'.join([self.ACCOUNTS_BASEURL, account, 'attr', key])
        url = build_url(choice(self.list_hosts), path=path)
        res = self._send_request(url, type_='DEL', data=None)
        if res.status_code == codes.ok:
            return True
        else:
            exc_cls, exc_msg = self._get_exception(headers=res.headers, status_code=res.status_code, data=res.content)
            raise exc_cls(exc_msg)
