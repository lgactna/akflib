import logging
from pathlib import Path

from akflib.core.disk.core import get_file_entry, open_file_system
from akflib.core.disk.slack import analyze_file_slack, insert_into_file_slack

logging.basicConfig(level=logging.DEBUG)


def test_slack() -> None:
    # Sample: writing to slack space of a file

    # Test writing to slack space, based on the example in the playground folder
    image_path = Path("C:\\Users\\Kisun\\Downloads\\decrypted-2.iso")
    data = b"Hello, world!"
    location = "Users\\user\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\agent.exe"

    # Open the filesystem, select largest partition by default
    fs, volume_info = open_file_system(image_path)

    # Get the file entry
    file_entry = get_file_entry(fs, location)
    # Analyze the slack space of the file
    meta = analyze_file_slack(file_entry, volume_info.volume_extent_offset)

    # Write data to slack space
    insert_into_file_slack(image_path, data, meta)


def test_rendering() -> None:
    # Sample: UCO bundle rendering
    from datetime import UTC, datetime
    from pprint import pprint

    from caselib import uco

    from akflib.rendering.objs import AKFBundle

    bundle_identity = uco.identity.Identity()
    bundle_identity_name = uco.identity.SimpleNameFacet(
        givenName="Maurice", familyName="Moss"
    )
    bundle_identity.hasFacet.append(bundle_identity_name)  # type: ignore[union-attr]

    bundle_created_time = datetime.strptime(
        "2024-04-28T21:38:19", "%Y-%m-%dT%H:%M:%S"
    ).astimezone(UTC)
    bundle_modified_time = datetime.strptime(
        "2024-05-02T21:38:19", "%Y-%m-%dT%H:%M:%S"
    ).astimezone(UTC)

    # This is an example of where bundle_identity ought to be passed in as a
    # reference. This means that only the @id field is attached to this node,
    # even though this is technically a copy of the "full" object.
    bundle = AKFBundle(
        createdBy=[bundle_identity.ref()],
        description="An Example Case File",
        modifiedTime=bundle_modified_time,
        name="json ld file",
        objectCreatedTime=bundle_created_time,
        specVersion="UCO/CASE 2.0",
        tag="Artifacts extracted from a mobile phone",
    )
    bundle.add_object(bundle_identity)

    email_address_object_1 = uco.observable.ObservableObject()
    email_address_1 = uco.observable.EmailAddressFacet(
        addressValue="info@example.com",
        displayName="Example User",
    )
    email_address_object_1.hasFacet.append(email_address_1)  # type: ignore[union-attr]

    email_account_object_1 = uco.observable.ObservableObject()
    account_1 = uco.observable.EmailAccountFacet(emailAddress=email_account_object_1)
    # If we don't use a reference here, we get infinite recursion
    email_account_object_1.hasFacet.append(account_1.ref())  # type: ignore[union-attr]

    bundle.add_object(email_account_object_1)

    pprint(dict(bundle._object_index))

def test_rendering_2() -> None:
    # Sample: UCO bundle rendering, but converted
    from datetime import UTC, datetime
    from pprint import pprint

    from caselib import uco

    from akflib.rendering.objs import AKFBundle
    from caselib.uco.core import Bundle

    bundle_identity = uco.identity.Identity()
    bundle_identity_name = uco.identity.SimpleNameFacet(
        givenName="Maurice", familyName="Moss"
    )
    bundle_identity.hasFacet.append(bundle_identity_name)  # type: ignore[union-attr]

    bundle_created_time = datetime.strptime(
        "2024-04-28T21:38:19", "%Y-%m-%dT%H:%M:%S"
    ).astimezone(UTC)
    bundle_modified_time = datetime.strptime(
        "2024-05-02T21:38:19", "%Y-%m-%dT%H:%M:%S"
    ).astimezone(UTC)

    # This is an example of where bundle_identity ought to be passed in as a
    # reference. This means that only the @id field is attached to this node,
    # even though this is technically a copy of the "full" object.
    bundle = Bundle(
        createdBy=[bundle_identity.ref()],
        description="An Example Case File",
        modifiedTime=bundle_modified_time,
        name="json ld file",
        objectCreatedTime=bundle_created_time,
        specVersion="UCO/CASE 2.0",
        tag="Artifacts extracted from a mobile phone",
    )
    bundle.object.append(bundle_identity)  # type: ignore[union-attr]

    email_address_object_1 = uco.observable.ObservableObject()
    email_address_1 = uco.observable.EmailAddressFacet(
        addressValue="info@example.com",
        displayName="Example User",
    )
    email_address_object_1.hasFacet.append(email_address_1)  # type: ignore[union-attr]

    email_account_object_1 = uco.observable.ObservableObject()
    account_1 = uco.observable.EmailAccountFacet(emailAddress=email_account_object_1)
    # If we don't use a reference here, we get infinite recursion
    email_account_object_1.hasFacet.append(account_1.ref())  # type: ignore[union-attr]

    bundle.object.extend([email_account_object_1, email_address_object_1])

    new_bundle = AKFBundle.from_bundle(bundle)
    pprint(dict(new_bundle._object_index))
    
    print(list(new_bundle._object_index.keys()))


if __name__ == "__main__":
    # test_slack()
    # test_rendering()
    test_rendering_2()
