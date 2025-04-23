## Range requests on Azure blob storage

```shell
$ az storage account blob-service-properties show -n musikensmakt
{
  ...
  "defaultServiceVersion": null,
  ...
}
$ az storage account blob-service-properties update -n musikensmakt --default-service-version 2025-05-05
{
  ...
  "defaultServiceVersion": "2025-05-05",
  ...
}
```

Reference:
https://learn.microsoft.com/en-us/rest/api/storageservices/Set-Blob-Service-Properties
https://stackoverflow.com/questions/17408927/do-http-range-headers-work-with-azure-blob-storage-shared-access-signatures

See current latest version:
https://learn.microsoft.com/en-us/rest/api/storageservices/versioning-for-the-azure-storage-services


## user-agents-v2

1. bots.json
2. apps.json
   1. devices.json
3. libraries.json
   1. devices.json
4. browsers.json
   1. devices.json
   2. referrers.json


geocoder.ip(ip)
get(ip, provider='ipinfo', **kwargs)
provider = "ipinfo"
method = "geocode"
func = options[provider][method] = options["ipinfo"]["geocode"] = IpinfoQuery
IpinfoQuery(ip, **kwargs)
IpinfoQuery < MultipleResultsQuery < typing.MutableSequence
