# EmploymentExperienceManifestV1Monitor


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**tiles** | [**List[EmploymentExperienceManifestV1MonitorTilesInner]**](EmploymentExperienceManifestV1MonitorTilesInner.md) |  | 
**narratives** | [**List[EmploymentExperienceManifestV1MonitorNarrativesInner]**](EmploymentExperienceManifestV1MonitorNarrativesInner.md) |  | 
**alerts** | [**List[EmploymentExperienceManifestV1MonitorAlertsInner]**](EmploymentExperienceManifestV1MonitorAlertsInner.md) |  | 

## Example

```python
from employment_domain_client.models.employment_experience_manifest_v1_monitor import EmploymentExperienceManifestV1Monitor

# TODO update the JSON string below
json = "{}"
# create an instance of EmploymentExperienceManifestV1Monitor from a JSON string
employment_experience_manifest_v1_monitor_instance = EmploymentExperienceManifestV1Monitor.from_json(json)
# print the JSON string representation of the object
print(EmploymentExperienceManifestV1Monitor.to_json())

# convert the object into a dict
employment_experience_manifest_v1_monitor_dict = employment_experience_manifest_v1_monitor_instance.to_dict()
# create an instance of EmploymentExperienceManifestV1Monitor from a dict
employment_experience_manifest_v1_monitor_from_dict = EmploymentExperienceManifestV1Monitor.from_dict(employment_experience_manifest_v1_monitor_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


