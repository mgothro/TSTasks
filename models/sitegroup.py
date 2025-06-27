from dbconn import execute_query
import calendar
from datetime import datetime, timedelta

class SiteGroup:
    all_sitegroups = []

    def __init__(self, sitegroup_id=None, directory=None, active_status=None):
        self.sitegroup_id = sitegroup_id
        self.directory = directory
        self.active_status = active_status
        SiteGroup.all_sitegroups.append(self)

    @classmethod
    def get_by_id(cls, sitegroup_id):
        for site in cls.all_sitegroups:
            if site.sitegroup_id == sitegroup_id:
                return site

        query = '''
            SELECT SiteGroupID, Directory, ActiveStatus
            FROM SiteGroupDataView
            WHERE SiteGroupID = ?
        '''
        row = execute_query(query, (sitegroup_id,), fetch_one=True)
        if row:
            return SiteGroup(*row)
        return None

    @classmethod
    def get_by_directory(cls, directory):
        for site in cls.all_sitegroups:
            if site.directory == directory:
                return site

        query = '''
            SELECT SiteGroupID, Directory, ActiveStatus
            FROM SiteGroupDataView
            WHERE Directory = ?
        '''
        row = execute_query(query, (directory,), fetch_one=True)
        if row:
            return SiteGroup(*row)
        return None

    @classmethod
    def get_all(cls):
        query = 'SELECT SiteGroupID, Directory, ActiveStatus FROM SiteGroupDataView'
        rows = execute_query(query, fetch_all=True)
        existing_ids = cls.get_sitegroup_ids()
        for row in rows:
            if row[0] not in existing_ids:
                SiteGroup(*row)
        return cls.all_sitegroups

    @classmethod
    def get_active(cls):
        cls.get_all()
        return (site for site in cls.all_sitegroups if site.active_status == 'Active')

    @classmethod
    def get_inactive(cls):
        cls.get_all()
        return (site for site in cls.all_sitegroups if site.active_status == 'Inactive')

    @classmethod
    def get_sitegroup_ids(cls):
        return {site.sitegroup_id for site in cls.all_sitegroups}
