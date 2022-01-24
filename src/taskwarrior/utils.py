from typing import List


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
