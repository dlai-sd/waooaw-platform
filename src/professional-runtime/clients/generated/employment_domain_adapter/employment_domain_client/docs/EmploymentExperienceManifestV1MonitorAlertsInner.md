# EmploymentExperienceManifestV1MonitorAlertsInner


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**signal** | **str** |  | 
**threshold** | **str** |  | 
**severity** | **str** |  | 
**channels** | **List[str]** |  | 

## Example

```python
from employment_domain_client.models.employment_experience_manifest_v1_monitor_alerts_inner import EmploymentExperienceManifestV1MonitorAlertsInner

# TODO update the JSON string below
json = "{}"
# create an instance of EmploymentExperienceManifestV1MonitorAlertsInner from a JSON string
employment_experience_manifest_v1_monitor_alerts_inner_instance = EmploymentExperienceManifestV1MonitorAlertsInner.from_json(json)
# print the JSON string representation of the object
print(EmploymentExperienceManifestV1MonitorAlertsInner.to_json())

# convert the object into a dict
employment_experience_manifest_v1_monitor_alerts_inner_dict = employment_experience_manifest_v1_monitor_alerts_inner_instance.to_dict()
# create an instance of EmploymentExperienceManifestV1MonitorAlertsInner from a dict
employment_experience_manifest_v1_monitor_alerts_inner_from_dict = EmploymentExperienceManifestV1MonitorAlertsInner.from_dict(employment_experience_manifest_v1_monitor_alerts_inner_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


