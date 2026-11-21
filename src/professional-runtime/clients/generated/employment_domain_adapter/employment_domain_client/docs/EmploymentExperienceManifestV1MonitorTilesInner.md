# EmploymentExperienceManifestV1MonitorTilesInner


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**tile_id** | **str** |  | 
**measure_id** | **str** |  | 
**block_type** | **str** |  | 
**audiences** | [**List[EmploymentExperienceAudienceV1]**](EmploymentExperienceAudienceV1.md) |  | 

## Example

```python
from employment_domain_client.models.employment_experience_manifest_v1_monitor_tiles_inner import EmploymentExperienceManifestV1MonitorTilesInner

# TODO update the JSON string below
json = "{}"
# create an instance of EmploymentExperienceManifestV1MonitorTilesInner from a JSON string
employment_experience_manifest_v1_monitor_tiles_inner_instance = EmploymentExperienceManifestV1MonitorTilesInner.from_json(json)
# print the JSON string representation of the object
print(EmploymentExperienceManifestV1MonitorTilesInner.to_json())

# convert the object into a dict
employment_experience_manifest_v1_monitor_tiles_inner_dict = employment_experience_manifest_v1_monitor_tiles_inner_instance.to_dict()
# create an instance of EmploymentExperienceManifestV1MonitorTilesInner from a dict
employment_experience_manifest_v1_monitor_tiles_inner_from_dict = EmploymentExperienceManifestV1MonitorTilesInner.from_dict(employment_experience_manifest_v1_monitor_tiles_inner_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


