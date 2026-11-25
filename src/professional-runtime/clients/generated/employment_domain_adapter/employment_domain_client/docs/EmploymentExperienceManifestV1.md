# EmploymentExperienceManifestV1

Optional declaration of how the agent's goals, plan, operation, monitoring and components are shown by the common workbench (agent-experience-contract.v1). A manifest without it stays admissible and is served by the legacy relationship projections. 

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**contract_version** | **str** |  | 
**vocabulary_ref** | [**ImmutableContractReferenceV1**](ImmutableContractReferenceV1.md) |  | 
**component_catalogue_ref** | [**ImmutableContractReferenceV1**](ImmutableContractReferenceV1.md) |  | [optional] 
**goal_types** | [**List[EmploymentExperienceGoalTypeV1]**](EmploymentExperienceGoalTypeV1.md) |  | 
**plan** | [**EmploymentExperienceManifestV1Plan**](EmploymentExperienceManifestV1Plan.md) |  | 
**operate** | [**EmploymentExperienceManifestV1Operate**](EmploymentExperienceManifestV1Operate.md) |  | 
**monitor** | [**EmploymentExperienceManifestV1Monitor**](EmploymentExperienceManifestV1Monitor.md) |  | 
**domain_blocks** | [**List[EmploymentExperienceManifestV1DomainBlocksInner]**](EmploymentExperienceManifestV1DomainBlocksInner.md) |  | 
**components** | [**List[EmploymentExperienceComponentV1]**](EmploymentExperienceComponentV1.md) |  | 
**audiences** | [**List[EmploymentExperienceAudienceV1]**](EmploymentExperienceAudienceV1.md) |  | 
**modalities** | **List[str]** |  | 
**channel_support** | [**EmploymentExperienceManifestV1ChannelSupport**](EmploymentExperienceManifestV1ChannelSupport.md) |  | 
**conformance_scenarios** | **List[str]** |  | 
**navigation** | [**List[EmploymentExperienceNavigationEntryV1]**](EmploymentExperienceNavigationEntryV1.md) | WC-171. Optional entries the agent adds after the platform&#39;s fixed surfaces in its context menu: data only (label, closed icon, order hint, surface kind). Admission refuses unknown surface kinds, markup, duplicate ids and entries that open nothing. A manifest without it shows only the fixed surfaces.  | [optional] 

## Example

```python
from employment_domain_client.models.employment_experience_manifest_v1 import EmploymentExperienceManifestV1

# TODO update the JSON string below
json = "{}"
# create an instance of EmploymentExperienceManifestV1 from a JSON string
employment_experience_manifest_v1_instance = EmploymentExperienceManifestV1.from_json(json)
# print the JSON string representation of the object
print(EmploymentExperienceManifestV1.to_json())

# convert the object into a dict
employment_experience_manifest_v1_dict = employment_experience_manifest_v1_instance.to_dict()
# create an instance of EmploymentExperienceManifestV1 from a dict
employment_experience_manifest_v1_from_dict = EmploymentExperienceManifestV1.from_dict(employment_experience_manifest_v1_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


