from typing import Any
from typing import Dict
from typing import List


def convert_config_output_to_dict(output: str) -> Dict[str, Any]:
    config: Dict[str, Any] = {}

    for line in output.split("\n"):
        comment_position = line.find("#")
        if comment_position < 0:
            line = line.strip()
        else:
            line = line[:comment_position].strip()

        if not line:
            continue

        left, right = line.split("=", 1)
        key_parts = left.strip().split(".")
        value = right.strip()

        cursor = config
        for part in key_parts[0:-1]:
            if part not in cursor:
                cursor[part] = {}

            if not isinstance(cursor[part], dict):
                cursor[part] = {}

            cursor = cursor[part]
        cursor[key_parts[-1]] = value

    return config


def convert_dict_to_override_args(config, prefix="") -> List[str]:
    """Converts a dictionary of override arguments into CLI arguments.

    * Converts leaf nodes into dot paths of key names leading to the leaf
      node.
    * Does not include paths to leaf nodes not being non-dictionary type.

    See `taskw.test.test_utils.TestUtils.test_convert_dict_to_override_args`
    for details.

    """
    args = []
    for k, v in config.items():
        if isinstance(v, dict):
            args.extend(
                convert_dict_to_override_args(
                    v,
                    prefix=".".join(
                        [
                            prefix,
                            k,
                        ]
                    )
                    if prefix
                    else k,
                )
            )
        else:
            v = str(v)
            left = "rc" + (("." + prefix) if prefix else "") + "." + k
            right = v if " " not in v else '"%s"' % v
            args.append("=".join([left, right]))
    return args
