### 由于模型文件过大 完整文件请移步[谷歌网盘](https://drive.google.com/file/d/1ZD8O-ZbWe_UFhll7QHWW9K2CvWb5qxPJ/view?usp=sharing)

---
tags:
- sentence-transformers
- sentence-similarity
- feature-extraction
- dense
- generated_from_trainer
- dataset_size:20624
- loss:CosineSimilarityLoss
base_model: microsoft/unixcoder-base
widget:
- source_sentence: "def is_monotonic(arr: list) -> bool:\n    \"\"\"\n    Check if\
    \ the given array is monotonic.\n\n    An array is monotonic if it is either entirely\
    \ non-increasing or non-decreasing.\n\n    Parameters:\n    arr (list): A list\
    \ of integers or floats.\n\n    Returns:\n    bool: True if the array is monotonic,\
    \ False otherwise.\n    \"\"\"\n    # Handle edge cases: empty array or array\
    \ with 1 element\n    if not arr or len(arr) == 1:\n        return True\n\n  \
    \  # Initialize flags to track increasing and decreasing trends\n    is_increasing\
    \ = True\n    is_decreasing = True\n\n    # Iterate through the array to check\
    \ trends\n    for i in range(1, len(arr)):\n        if arr[i] > arr[i - 1]:\n\
    \            is_decreasing = False  # Not decreasing\n        if arr[i] < arr[i\
    \ - 1]:\n            is_increasing = False  # Not increasing\n\n        # Early\
    \ exit if both flags are False\n        if not is_increasing and not is_decreasing:\n\
    \            return False\n\n    # If either flag is still True, the array is\
    \ monotonic\n    return is_increasing or is_decreasing\n\n\n# Example usage and\
    \ testing\nif __name__ == \"__main__\":\n    test_cases = [\n        [1, 2, 3,\
    \ 4, 5],  # Monotonic increasing\n        [5, 4, 3, 2, 1],  # Monotonic decreasing\n\
    \        [1, 1, 1, 1],     # All elements equal (monotonic)\n        [1, 3, 2,\
    \ 4],     # Not monotonic\n        [],               # Empty array\n        [42],\
    \             # Single element\n        [1, 2, 2, 3],     # Non-decreasing with\
    \ duplicates\n        [3, 2, 2, 1]      # Non-increasing with duplicates\n   \
    \ ]\n\n    for test in test_cases:\n        result = is_monotonic(test)\n    \
    \    print(f\"Input: {test}\")\n        print(f\"Is monotonic? {result}\")\n \
    \       print(\"---\")\n"
  sentences:
  - "def check_monotonic(array):\n    if not array:\n        return True\n    \n \
    \   increasing = decreasing = True\n    for i in range(len(array) - 1):\n    \
    \    if array[i] < array[i + 1]:\n            decreasing = False\n        elif\
    \ array[i] > array[i + 1]:\n            increasing = False\n    \n    return increasing\
    \ or decreasing\n"
  - "def calculate_loss(original_price, selling_price):\n    if selling_price > original_price:\n\
    \        loss = selling_price - original_price\n        return loss\n    else:\n\
    \        return None\n"
  - "def round_and_sum(list1):\n\n  lenght=len(list1)\n\n  round_and_sum=sum(list(map(round,list1))*\
    \ lenght)\n\n  return round_and_sum\n"
- source_sentence: "def split_at_uppercase(input_string: str) -> list:\n    \"\"\"\
    \n    Splits a string at uppercase letters and returns a list of the resulting\
    \ substrings.\n\n    Parameters:\n    input_string (str): The string to be split.\n\
    \n    Returns:\n    list: A list of substrings obtained by splitting the input\
    \ string at uppercase letters.\n    \"\"\"\n    # Initialize an empty list to\
    \ store the resulting substrings\n    substrings = []\n    # Initialize a variable\
    \ to keep track of the start index of the current substring\n    start = 0\n\n\
    \    # Iterate through the string to find uppercase letters\n    for i, char in\
    \ enumerate(input_string):\n        if char.isupper() and i != start:  # Check\
    \ if the character is uppercase and not the first character\n            # Append\
    \ the substring from start to the current index (excluding the uppercase character)\n\
    \            substrings.append(input_string[start:i])\n            # Update the\
    \ start index to the current position\n            start = i\n\n    # Append the\
    \ last substring (from the last start index to the end of the string)\n    substrings.append(input_string[start:])\n\
    \n    return substrings\n\n\n# Example usage and testing\nif __name__ == \"__main__\"\
    :\n    # Test cases\n    test_strings = [\n        \"HelloWorld\",  # Normal case\n\
    \        \"SplitAtUpperCase\",  # Multiple uppercase letters\n        \"noUppercaseHere\"\
    ,  # Only one uppercase letter\n        \"ALLUPPERCASE\",  # All uppercase letters\n\
    \        \"\",  # Empty string\n        \"single\",  # No uppercase letters\n\
    \        \"CamelCaseExample\"  # Mixed case\n    ]\n\n    for test in test_strings:\n\
    \        result = split_at_uppercase(test)\n        print(f\"Input: '{test}'\"\
    )\n        print(f\"Output: {result}\")\n        print(\"---\")\n"
  sentences:
  - "def is_nested_subset(subset, superset):\n    \"\"\"\n    Check if a nested list\
    \ is a subset of another nested list.\n\n    Parameters:\n    subset (list): The\
    \ nested list to check if it's a subset.\n    superset (list): The nested list\
    \ to check against.\n\n    Returns:\n    bool: True if `subset` is a subset of\
    \ `superset`, False otherwise.\n    \"\"\"\n    # Base case: If the subset is\
    \ empty, it's always a subset\n    if not subset:\n        return True\n\n   \
    \ # Base case: If the superset is empty but the subset is not, it's not a subset\n\
    \    if not superset:\n        return False\n\n    # If the first element of the\
    \ subset is a list, recursively check if it's a subset\n    if isinstance(subset[0],\
    \ list):\n        # Check if the first element of the subset is a subset of any\
    \ element in the superset\n        for element in superset:\n            if isinstance(element,\
    \ list) and is_nested_subset(subset[0], element):\n                # If found,\
    \ recursively check the rest of the subset\n                return is_nested_subset(subset[1:],\
    \ superset)\n        return False\n    else:\n        # If the first element of\
    \ the subset is not a list, check if it exists in the superset\n        if subset[0]\
    \ in superset:\n            # If found, recursively check the rest of the subset\n\
    \            return is_nested_subset(subset[1:], superset)\n        return False\n\
    \n\n# Example usage and test cases\nif __name__ == \"__main__\":\n    # Test cases\n\
    \    test_cases = [\n        ([[1, 2], [3, 4]], [[1, 2], [3, 4], [5, 6]]),  #\
    \ True\n        ([[1, 2]], [[3, 4], [5, 6]]),                  # False\n     \
    \   ([1, [2, 3]], [1, [2, 3], 4]),                 # True\n        ([], [[1, 2],\
    \ [3, 4]]),                        # True (empty subset)\n        ([[1, 2]], []),\
    \                                # False (empty superset)\n        ([[1, 2]],\
    \ [[1, [2]]]),                        # False (nested mismatch)\n        ([[1,\
    \ [2, 3]]], [[1, [2, 3]]]),                # True (exact match)\n    ]\n\n   \
    \ for subset, superset in test_cases:\n        result = is_nested_subset(subset,\
    \ superset)\n        print(f\"Subset: {subset}\")\n        print(f\"Superset:\
    \ {superset}\")\n        print(f\"Is subset? {result}\")\n        print(\"---\"\
    )\n"
  - "import re\n\ndef split_list(text):\n    # Reordered logic: first define the pattern,\
    \ then apply it\n    pattern = '[A-Z][^A-Z]*'\n    matches = re.findall(pattern,\
    \ text)\n    return matches\n"
  - "def multiply_consecutive(numbers):\n    \"\"\"\n    Multiplies consecutive numbers\
    \ in the given list.\n    \n    Parameters:\n    numbers (list): A list of numbers\
    \ to multiply.\n    \n    Returns:\n    list: A new list containing the products\
    \ of consecutive numbers.\n    \"\"\"\n    # Check if the list has less than 2\
    \ elements\n    if len(numbers) < 2:\n        return []  # If so, return an empty\
    \ list as no multiplication can be performed\n    \n    # Initialize an empty\
    \ list to store the products\n    products = []\n    \n    # Iterate through the\
    \ list up to the second last element\n    for i in range(len(numbers) - 1):\n\
    \        # Multiply the current number by the next number\n        product = numbers[i]\
    \ * numbers[i + 1]\n        # Append the product to the products list\n      \
    \  products.append(product)\n    \n    return products  # Return the list of products\n\
    \n\ndef main():\n    # Example usage of the multiply_consecutive function\n  \
    \  sample_list = [2, 3, 5, 7, 11]\n    result = multiply_consecutive(sample_list)\n\
    \    print(\"Original List:\", sample_list)\n    print(\"Products of Consecutive\
    \ Numbers:\", result)\n\n\nif __name__ == \"__main__\":\n    main()\n"
- source_sentence: "def remove_odd_characters(input_string: str) -> str:\n    \"\"\
    \"\n    Removes characters at odd indices from the input string.\n\n    Parameters:\n\
    \    input_string (str): The string from which to remove characters at odd indices.\n\
    \n    Returns:\n    str: A new string with characters at odd indices removed.\n\
    \    \"\"\"\n    # Use list comprehension to iterate through the string and keep\
    \ only even-indexed characters\n    # Enumerate is used to get both the index\
    \ and the character\n    result = ''.join([char for index, char in enumerate(input_string)\
    \ if index % 2 == 0])\n    \n    return result\n\n# Example usage and testing\n\
    if __name__ == \"__main__\":\n    # Test cases\n    test_cases = [\n        \"\
    abcdef\",       # Normal case\n        \"hello\",        # Odd-length string\n\
    \        \"\",             # Empty string\n        \"a\",            # Single\
    \ character\n        \"1234567890\",   # String with numbers\n        \"  \",\
    \           # String with spaces\n        \"!@#$%^&*()\"    # String with special\
    \ characters\n    ]\n\n    for test in test_cases:\n        print(f\"Input: '{test}'\"\
    )\n        print(f\"Output: '{remove_odd_characters(test)}'\")\n        print(\"\
    ---\")\n"
  sentences:
  - "def value_exists(sequence, value):\n    \"\"\"\n    Check whether a value exists\
    \ in a given sequence.\n\n    Parameters:\n    sequence (list, tuple, str, etc.):\
    \ The sequence to search in.\n    value: The value to search for.\n\n    Returns:\n\
    \    bool: True if the value exists in the sequence, False otherwise.\n    \"\"\
    \"\n    # Use Python's 'in' operator to check for membership\n    return value\
    \ in sequence\n\n# Example usage and testing\nif __name__ == \"__main__\":\n \
    \   # Test cases\n    test_cases = [\n        ([1, 2, 3, 4, 5], 3),        # Value\
    \ exists in a list\n        ((\"apple\", \"banana\", \"cherry\"), \"orange\"),\
    \  # Value does not exist in a tuple\n        (\"hello world\", \"o\"),      \
    \  # Value exists in a string\n        ([], 42),                    # Empty sequence\n\
    \        ({1, 2, 3}, 2),              # Value exists in a set\n        ({\"name\"\
    : \"Alice\", \"age\": 25}, \"Alice\")  # Value exists in a dictionary (checks\
    \ keys)\n    ]\n\n    for sequence, value in test_cases:\n        result = value_exists(sequence,\
    \ value)\n        print(f\"Sequence: {sequence}\")\n        print(f\"Value: {value}\"\
    )\n        print(f\"Exists: {result}\")\n        print(\"---\")\n"
  - "def filter_even_chars(input_str):\n    result_str = ''\n    for index in range(1,\
    \ len(input_str) + 1):\n        if index % 2 == 0:\n            result_str +=\
    \ input_str[index - 1]\n    return result_str\n"
  - "def sort_mixed_list(mixed_list):\n    str_part = sorted([i for i in mixed_list\
    \ if type(i) is str])\n    int_part = sorted([i for i in mixed_list if type(i)\
    \ is int])\n    return int_part + str_part\n"
- source_sentence: "def count_inversions(arr: list) -> int:\n    \"\"\"\n    Count\
    \ the number of inversions in the given array using a modified Merge Sort approach.\n\
    \n    An inversion is a pair of indices (i, j) such that i < j and arr[i] > arr[j].\n\
    \n    Parameters:\n    arr (list): The input array of integers.\n\n    Returns:\n\
    \    int: The total number of inversions in the array.\n    \"\"\"\n    # Helper\
    \ function to perform merge sort and count inversions\n    def merge_sort_and_count(arr:\
    \ list) -> tuple[list, int]:\n        # Base case: if the array has 0 or 1 element,\
    \ it is already sorted, and there are no inversions\n        if len(arr) <= 1:\n\
    \            return arr, 0\n\n        # Split the array into two halves\n    \
    \    mid = len(arr) // 2\n        left, left_count = merge_sort_and_count(arr[:mid])\
    \  # Sort the left half and count inversions\n        right, right_count = merge_sort_and_count(arr[mid:])\
    \  # Sort the right half and count inversions\n\n        # Merge the two sorted\
    \ halves and count split inversions\n        merged, split_count = merge_and_count(left,\
    \ right)\n\n        # Total inversions = inversions in left + inversions in right\
    \ + split inversions\n        total_count = left_count + right_count + split_count\n\
    \        return merged, total_count\n\n    def merge_and_count(left: list, right:\
    \ list) -> tuple[list, int]:\n        merged = []\n        i = j = 0\n       \
    \ split_count = 0\n\n        # Merge the two sorted arrays while counting inversions\n\
    \        while i < len(left) and j < len(right):\n            if left[i] <= right[j]:\n\
    \                merged.append(left[i])\n                i += 1\n            else:\n\
    \                merged.append(right[j])\n                j += 1\n           \
    \     # If left[i] > right[j], it forms inversions with all remaining elements\
    \ in the left array\n                split_count += len(left) - i\n\n        #\
    \ Append any remaining elements from left or right\n        merged.extend(left[i:])\n\
    \        merged.extend(right[j:])\n\n        return merged, split_count\n\n  \
    \  # Call the helper function and return the total number of inversions\n    _,\
    \ total_inversions = merge_sort_and_count(arr)\n    return total_inversions\n\n\
    \n# Example usage and testing\nif __name__ == \"__main__\":\n    test_cases =\
    \ [\n        [1, 2, 3, 4, 5],  # No inversions\n        [5, 4, 3, 2, 1],  # Maximum\
    \ inversions\n        [2, 4, 1, 3, 5],  # Some inversions\n        [],       \
    \        # Empty array\n        [1],              # Single element\n        [3,\
    \ 1, 2, 4, 5],  # Partial inversions\n    ]\n\n    for test in test_cases:\n \
    \       result = count_inversions(test)\n        print(f\"Input: {test}\")\n \
    \       print(f\"Number of inversions: {result}\")\n        print(\"---\")\n"
  sentences:
  - "import heapq\n\ndef convert_to_heap(arr: list) -> list:\n    \"\"\"\n    Converts\
    \ an arbitrary list into a heap using the heap queue algorithm.\n\n    Parameters:\n\
    \    arr (list): The input list to be converted into a heap.\n\n    Returns:\n\
    \    list: The heapified list (in-place modification).\n    \"\"\"\n    # Edge\
    \ case: If the input is empty or None, return it as is\n    if arr is None or\
    \ len(arr) == 0:\n        return arr\n\n    # Use heapq.heapify to convert the\
    \ list into a heap in-place\n    heapq.heapify(arr)\n\n    return arr\n\n# Example\
    \ usage\nif __name__ == \"__main__\":\n    # Test cases\n    test_cases = [\n\
    \        [3, 1, 5, 7, 4, 2],  # Normal case\n        [],                  # Empty\
    \ list\n        [42],                # Single element\n        [5, 5, 5, 5], \
    \       # All elements are the same\n        [9, 8, 7, 6, 5, 4],  # Already in\
    \ descending order\n        [1, 2, 3, 4, 5, 6]   # Already in ascending order\n\
    \    ]\n\n    for test in test_cases:\n        print(f\"Original list: {test}\"\
    )\n        heap = convert_to_heap(test)\n        print(f\"Heapified list: {heap}\"\
    )\n        print(\"---\")\n"
  - "def find_max_value(record_list, index):\n    \"\"\"\n    Function to find the\
    \ maximum value from a list of tuples based on a specified index attribute.\n\
    \    \n    Parameters:\n    record_list (list): A list of tuples, where each tuple\
    \ contains multiple attributes.\n    index (int): The index of the attribute to\
    \ compare for maximum value.\n    \n    Returns:\n    tuple: The tuple that has\
    \ the maximum value for the specified index attribute.\n           Returns None\
    \ if the list is empty or index is out of range.\n    \"\"\"\n    # Check if the\
    \ record list is empty\n    if not record_list:\n        return None\n\n    #\
    \ Initialize the maximum value and the corresponding tuple\n    max_value = float('-inf')\
    \  # Start with the smallest possible value\n    max_record = None\n\n    # Iterate\
    \ through each record in the record list\n    for record in record_list:\n   \
    \     # Ensure the index is within the bounds of the tuple\n        if index <\
    \ len(record):\n            current_value = record[index]\n            # Update\
    \ max_value and max_record if the current value is greater\n            if current_value\
    \ > max_value:\n                max_value = current_value\n                max_record\
    \ = record\n        else:\n            print(f\"Warning: Index {index} is out\
    \ of range for record {record}\")\n    \n    return max_record\n\n# Example usage:\n\
    if __name__ == \"__main__\":\n    records = [\n        (1, 'Alice', 23),\n   \
    \     (2, 'Bob', 30),\n        (3, 'Charlie', 25),\n        (4, 'Diana', 30),\n\
    \    ]\n    \n    # Find the record with the maximum age (index 2)\n    max_record\
    \ = find_max_value(records, 2)\n    \n    if max_record is not None:\n       \
    \ print(f\"The record with the maximum value is: {max_record}\")\n    else:\n\
    \        print(\"No records found.\")\n"
  - "def sum_between_indices(lst: list, start: int, end: int) -> int:\n    \"\"\"\n\
    \    Calculate the sum of the numbers in a list between the specified indices\
    \ (inclusive).\n\n    Parameters:\n    lst (list): The list of numbers.\n    start\
    \ (int): The starting index (inclusive).\n    end (int): The ending index (inclusive).\n\
    \n    Returns:\n    int: The sum of the numbers between the indices, or 0 if the\
    \ indices are invalid.\n    \"\"\"\n    # Handle edge cases: empty list or invalid\
    \ indices\n    if not lst or start < 0 or end >= len(lst) or start > end:\n  \
    \      return 0\n\n    # Use slicing to get the sublist and calculate the sum\n\
    \    sublist = lst[start:end + 1]\n    return sum(sublist)\n\n# Example usage\n\
    if __name__ == \"__main__\":\n    # Test cases\n    test_cases = [\n        ([1,\
    \ 2, 3, 4, 5], 1, 3),  # Normal case\n        ([10, 20, 30, 40], 0, 2), # Start\
    \ at 0\n        ([5, 10, 15], 2, 2),      # Single element\n        ([], 0, 0),\
    \               # Empty list\n        ([1, 2, 3], -1, 2),       # Invalid start\
    \ index\n        ([1, 2, 3], 1, 5),        # Invalid end index\n        ([1, 2,\
    \ 3], 2, 1)         # Start > end\n    ]\n\n    for lst, start, end in test_cases:\n\
    \        result = sum_between_indices(lst, start, end)\n        print(f\"List:\
    \ {lst}, Start: {start}, End: {end}\")\n        print(f\"Sum between indices:\
    \ {result}\")\n        print(\"---\")\n"
- source_sentence: "def find_min_length_list(lists: list[list]) -> list:\n    \"\"\
    \"\n    Find the list with the minimum length from a list of lists using a lambda\
    \ function.\n\n    Parameters:\n    lists (list[list]): A list containing multiple\
    \ lists.\n\n    Returns:\n    list: The list with the minimum length. If the input\
    \ is empty, returns None.\n    \"\"\"\n    # Handle edge case: empty input\n \
    \   if not lists:\n        return None\n\n    # Use the min() function with a\
    \ lambda as the key to find the list with the minimum length\n    return min(lists,\
    \ key=lambda x: len(x))\n\n# Example usage\nif __name__ == \"__main__\":\n   \
    \ test_cases = [\n        [[1, 2, 3], [4, 5], [6]],  # Normal case\n        [[],\
    \ [1], [2, 3]],         # Contains an empty list\n        [[1]],             \
    \        # Single list\n        [],                        # Empty input\n   \
    \     [[1, 2], [3, 4], [5, 6]]   # All lists of the same length\n    ]\n\n   \
    \ for test in test_cases:\n        result = find_min_length_list(test)\n     \
    \   print(f\"Input: {test}\")\n        print(f\"List with minimum length: {result}\"\
    )\n        print(\"---\")\n"
  sentences:
  - "def snake_to_camel(snake_str: str) -> str:\n    \"\"\"\n    Convert a snake_case\
    \ string to camelCase.\n\n    Parameters:\n    snake_str (str): The input string\
    \ in snake_case format.\n\n    Returns:\n    str: The converted string in camelCase\
    \ format.\n    \"\"\"\n    # Split the snake_case string into parts using underscore\
    \ as the delimiter\n    parts = snake_str.split('_')\n    \n    # Handle edge\
    \ case: if the string is empty or has no underscores\n    if not parts:\n    \
    \    return snake_str\n    \n    # Capitalize the first letter of each part except\
    \ the first one\n    camel_case = parts[0] + ''.join(word.capitalize() for word\
    \ in parts[1:])\n    \n    return camel_case\n\n# Example usage and testing\n\
    if __name__ == \"__main__\":\n    test_cases = [\n        \"hello_world\",   \
    \    # Basic case\n        \"this_is_a_test\",    # Multiple underscores\n   \
    \     \"single\",            # No underscores\n        \"\",                 \
    \ # Empty string\n        \"_leading_underscore\",  # Leading underscore\n   \
    \     \"trailing_underscore_\", # Trailing underscore\n        \"multiple__underscores\"\
    \ # Multiple consecutive underscores\n    ]\n\n    for test in test_cases:\n \
    \       result = snake_to_camel(test)\n        print(f\"Input: '{test}'\")\n \
    \       print(f\"Output: '{result}'\")\n        print(\"---\")\n"
  - "def filter_odd_numbers(numbers: list) -> list:\n    \"\"\"\n    Filters out odd\
    \ numbers from a list using a lambda function.\n\n    Parameters:\n    numbers\
    \ (list): A list of integers.\n\n    Returns:\n    list: A list containing only\
    \ the even numbers from the input list.\n    \"\"\"\n    # Use the filter() function\
    \ with a lambda to check for even numbers\n    # The lambda function returns True\
    \ if the number is even (num % 2 == 0)\n    filtered_numbers = list(filter(lambda\
    \ num: num % 2 == 0, numbers))\n\n    return filtered_numbers\n\n\n# Example usage\n\
    if __name__ == \"__main__\":\n    # Test cases to verify the function\n    test_cases\
    \ = [\n        [1, 2, 3, 4, 5, 6],  # Mixed odd and even numbers\n        [2,\
    \ 4, 6, 8],        # All even numbers\n        [1, 3, 5, 7],        # All odd\
    \ numbers\n        [],                  # Empty list\n        [0],           \
    \      # Single even number\n        [-2, -1, 0, 1, 2]    # Negative and positive\
    \ numbers\n    ]\n\n    for test in test_cases:\n        result = filter_odd_numbers(test)\n\
    \        print(f\"Input: {test}\")\n        print(f\"Filtered (even numbers only):\
    \ {result}\")\n        print(\"---\")\n"
  - "def calculate_arc_length(diameter, angle):\n    pi_value = 22 / 7\n    if angle\
    \ >= 360:\n        return None\n    arc_length = (pi_value * diameter) * (angle\
    \ / 360)\n    return arc_length\n"
pipeline_tag: sentence-similarity
library_name: sentence-transformers
metrics:
- cosine_accuracy
- cosine_accuracy_threshold
- cosine_f1
- cosine_f1_threshold
- cosine_precision
- cosine_recall
- cosine_ap
- cosine_mcc
model-index:
- name: SentenceTransformer based on microsoft/unixcoder-base
  results:
  - task:
      type: binary-classification
      name: Binary Classification
    dataset:
      name: skyoj val
      type: skyoj-val
    metrics:
    - type: cosine_accuracy
      value: 0.9908376963350786
      name: Cosine Accuracy
    - type: cosine_accuracy_threshold
      value: 0.6785616874694824
      name: Cosine Accuracy Threshold
    - type: cosine_f1
      value: 0.9906040268456375
      name: Cosine F1
    - type: cosine_f1_threshold
      value: 0.6785616874694824
      name: Cosine F1 Threshold
    - type: cosine_precision
      value: 0.9919354838709677
      name: Cosine Precision
    - type: cosine_recall
      value: 0.9892761394101877
      name: Cosine Recall
    - type: cosine_ap
      value: 0.996973448625503
      name: Cosine Ap
    - type: cosine_mcc
      value: 0.9816674516058082
      name: Cosine Mcc
---

# SentenceTransformer based on microsoft/unixcoder-base

This is a [sentence-transformers](https://www.SBERT.net) model finetuned from [microsoft/unixcoder-base](https://huggingface.co/microsoft/unixcoder-base). It maps sentences & paragraphs to a 768-dimensional dense vector space and can be used for semantic textual similarity, semantic search, paraphrase mining, text classification, clustering, and more.

## Model Details

### Model Description
- **Model Type:** Sentence Transformer
- **Base model:** [microsoft/unixcoder-base](https://huggingface.co/microsoft/unixcoder-base) <!-- at revision 5604afdc964f6c53782a6813140ade5216b99006 -->
- **Maximum Sequence Length:** 512 tokens
- **Output Dimensionality:** 768 dimensions
- **Similarity Function:** Cosine Similarity
<!-- - **Training Dataset:** Unknown -->
<!-- - **Language:** Unknown -->
<!-- - **License:** Unknown -->

### Model Sources

- **Documentation:** [Sentence Transformers Documentation](https://sbert.net)
- **Repository:** [Sentence Transformers on GitHub](https://github.com/huggingface/sentence-transformers)
- **Hugging Face:** [Sentence Transformers on Hugging Face](https://huggingface.co/models?library=sentence-transformers)

### Full Model Architecture

```
SentenceTransformer(
  (0): Transformer({'max_seq_length': 512, 'do_lower_case': False, 'architecture': 'RobertaModel'})
  (1): Pooling({'word_embedding_dimension': 768, 'pooling_mode_cls_token': False, 'pooling_mode_mean_tokens': True, 'pooling_mode_max_tokens': False, 'pooling_mode_mean_sqrt_len_tokens': False, 'pooling_mode_weightedmean_tokens': False, 'pooling_mode_lasttoken': False, 'include_prompt': True})
)
```

## Usage

### Direct Usage (Sentence Transformers)

First install the Sentence Transformers library:

```bash
pip install -U sentence-transformers
```

Then you can load this model and run inference.
```python
from sentence_transformers import SentenceTransformer

# Download from the 🤗 Hub
model = SentenceTransformer("sentence_transformers_model_id")
# Run inference
sentences = [
    'def find_min_length_list(lists: list[list]) -> list:\n    """\n    Find the list with the minimum length from a list of lists using a lambda function.\n\n    Parameters:\n    lists (list[list]): A list containing multiple lists.\n\n    Returns:\n    list: The list with the minimum length. If the input is empty, returns None.\n    """\n    # Handle edge case: empty input\n    if not lists:\n        return None\n\n    # Use the min() function with a lambda as the key to find the list with the minimum length\n    return min(lists, key=lambda x: len(x))\n\n# Example usage\nif __name__ == "__main__":\n    test_cases = [\n        [[1, 2, 3], [4, 5], [6]],  # Normal case\n        [[], [1], [2, 3]],         # Contains an empty list\n        [[1]],                     # Single list\n        [],                        # Empty input\n        [[1, 2], [3, 4], [5, 6]]   # All lists of the same length\n    ]\n\n    for test in test_cases:\n        result = find_min_length_list(test)\n        print(f"Input: {test}")\n        print(f"List with minimum length: {result}")\n        print("---")\n',
    'def snake_to_camel(snake_str: str) -> str:\n    """\n    Convert a snake_case string to camelCase.\n\n    Parameters:\n    snake_str (str): The input string in snake_case format.\n\n    Returns:\n    str: The converted string in camelCase format.\n    """\n    # Split the snake_case string into parts using underscore as the delimiter\n    parts = snake_str.split(\'_\')\n    \n    # Handle edge case: if the string is empty or has no underscores\n    if not parts:\n        return snake_str\n    \n    # Capitalize the first letter of each part except the first one\n    camel_case = parts[0] + \'\'.join(word.capitalize() for word in parts[1:])\n    \n    return camel_case\n\n# Example usage and testing\nif __name__ == "__main__":\n    test_cases = [\n        "hello_world",       # Basic case\n        "this_is_a_test",    # Multiple underscores\n        "single",            # No underscores\n        "",                  # Empty string\n        "_leading_underscore",  # Leading underscore\n        "trailing_underscore_", # Trailing underscore\n        "multiple__underscores" # Multiple consecutive underscores\n    ]\n\n    for test in test_cases:\n        result = snake_to_camel(test)\n        print(f"Input: \'{test}\'")\n        print(f"Output: \'{result}\'")\n        print("---")\n',
    'def filter_odd_numbers(numbers: list) -> list:\n    """\n    Filters out odd numbers from a list using a lambda function.\n\n    Parameters:\n    numbers (list): A list of integers.\n\n    Returns:\n    list: A list containing only the even numbers from the input list.\n    """\n    # Use the filter() function with a lambda to check for even numbers\n    # The lambda function returns True if the number is even (num % 2 == 0)\n    filtered_numbers = list(filter(lambda num: num % 2 == 0, numbers))\n\n    return filtered_numbers\n\n\n# Example usage\nif __name__ == "__main__":\n    # Test cases to verify the function\n    test_cases = [\n        [1, 2, 3, 4, 5, 6],  # Mixed odd and even numbers\n        [2, 4, 6, 8],        # All even numbers\n        [1, 3, 5, 7],        # All odd numbers\n        [],                  # Empty list\n        [0],                 # Single even number\n        [-2, -1, 0, 1, 2]    # Negative and positive numbers\n    ]\n\n    for test in test_cases:\n        result = filter_odd_numbers(test)\n        print(f"Input: {test}")\n        print(f"Filtered (even numbers only): {result}")\n        print("---")\n',
]
embeddings = model.encode(sentences)
print(embeddings.shape)
# [3, 768]

# Get the similarity scores for the embeddings
similarities = model.similarity(embeddings, embeddings)
print(similarities)
# tensor([[1.0000, 0.0129, 0.0322],
#         [0.0129, 1.0000, 0.0206],
#         [0.0322, 0.0206, 1.0000]])
```

<!--
### Direct Usage (Transformers)

<details><summary>Click to see the direct usage in Transformers</summary>

</details>
-->

<!--
### Downstream Usage (Sentence Transformers)

You can finetune this model on your own dataset.

<details><summary>Click to expand</summary>

</details>
-->

<!--
### Out-of-Scope Use

*List how the model may foreseeably be misused and address what users ought not to do with the model.*
-->

## Evaluation

### Metrics

#### Binary Classification

* Dataset: `skyoj-val`
* Evaluated with [<code>BinaryClassificationEvaluator</code>](https://sbert.net/docs/package_reference/sentence_transformer/evaluation.html#sentence_transformers.evaluation.BinaryClassificationEvaluator)

| Metric                    | Value     |
|:--------------------------|:----------|
| cosine_accuracy           | 0.9908    |
| cosine_accuracy_threshold | 0.6786    |
| cosine_f1                 | 0.9906    |
| cosine_f1_threshold       | 0.6786    |
| cosine_precision          | 0.9919    |
| cosine_recall             | 0.9893    |
| **cosine_ap**             | **0.997** |
| cosine_mcc                | 0.9817    |

<!--
## Bias, Risks and Limitations

*What are the known or foreseeable issues stemming from this model? You could also flag here known failure cases or weaknesses of the model.*
-->

<!--
### Recommendations

*What are recommendations with respect to the foreseeable issues? For example, filtering explicit content.*
-->

## Training Details

### Training Dataset

#### Unnamed Dataset

* Size: 20,624 training samples
* Columns: <code>sentence_0</code>, <code>sentence_1</code>, and <code>label</code>
* Approximate statistics based on the first 1000 samples:
  |         | sentence_0                                                                            | sentence_1                                                                           | label                                                          |
  |:--------|:--------------------------------------------------------------------------------------|:-------------------------------------------------------------------------------------|:---------------------------------------------------------------|
  | type    | string                                                                                | string                                                                               | float                                                          |
  | details | <ul><li>min: 196 tokens</li><li>mean: 394.76 tokens</li><li>max: 512 tokens</li></ul> | <ul><li>min: 19 tokens</li><li>mean: 246.16 tokens</li><li>max: 512 tokens</li></ul> | <ul><li>min: 0.0</li><li>mean: 0.49</li><li>max: 1.0</li></ul> |
* Samples:
  | sentence_0                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | sentence_1                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | label            |
  |:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:-----------------|
  | <code>def find_max_product_pair(arr: list) -> tuple[int, int] \| None:<br>    """<br>    Find the pair of integers in the array with the highest product.<br><br>    Parameters:<br>    arr (list): A list of integers.<br><br>    Returns:<br>    tuple[int, int] \| None: The pair of integers with the highest product, or None if the array has fewer than 2 elements.<br>    """<br>    # Handle edge cases: array with fewer than 2 elements<br>    if len(arr) < 2:<br>        return None<br><br>    # Initialize variables to track the two largest and two smallest numbers<br>    # (since the product of two negative numbers can also be large)<br>    max1, max2 = float('-inf'), float('-inf')  # Two largest numbers<br>    min1, min2 = float('inf'), float('inf')    # Two smallest numbers<br><br>    for num in arr:<br>        # Update the two largest numbers<br>        if num > max1:<br>            max2 = max1<br>            max1 = num<br>        elif num > max2:<br>            max2 = num<br><br>        # Update the two smallest numbers<br>        if num < min1:<br>            min2 = min1<br>       ...</code>        | <code>def max_product(arr):<br>    # Determine the length of the input array<br>    arr_length = len(arr)<br>    # Ensure there are at least two elements to form a pair<br>    if arr_length < 2:<br>        return "No pairs exist"<br>    x = arr[0]  # Start with the first element as x<br>    y = arr[1]  # Start with the second element as y<br>    # Loop through each element in the array<br>    for i in range(0, arr_length):<br>        for j in range(i + 1, arr_length):<br>            # Check if the current pair's product is greater than the previously recorded maximum<br>            if arr[i] * arr[j] > x * y:<br>                x = arr[i]  # Update x to the current element<br>                y = arr[j]  # Update y to the next element<br>    return x, y  # Return the pair that has the highest product<br></code> | <code>1.0</code> |
  | <code>import math<br><br>def calculate_arc_length(radius, angle_degrees):<br>    """<br>    Calculate the arc length of a given angle in a circle.<br><br>    Parameters:<br>    radius (float): The radius of the circle.<br>    angle_degrees (float): The angle in degrees.<br><br>    Returns:<br>    float: The arc length corresponding to the angle in the circle.<br>    """<br>    # Convert the angle from degrees to radians<br>    angle_radians = angle_degrees * (math.pi / 180)<br>    <br>    # Calculate the arc length using the formula: Arc Length = r * θ<br>    arc_length = radius * angle_radians<br>    <br>    return arc_length<br><br>def main():<br>    # Example usage of the function<br>    radius = 5.0  # Example radius in units<br>    angle = 60.0  # Example angle in degrees<br><br>    # Calculate the arc length<br>    arc_length = calculate_arc_length(radius, angle)<br>    <br>    # Print the result<br>    print(f"The arc length for a radius of {radius} and an angle of {angle} degrees is: {arc_length:.2f} units")<br><br>if __name__ == "__main__":<br>    main()<br></code>                          | <code>def calculate_arc_length(diameter, angle):<br>    pi_value = 22 / 7<br>    if angle >= 360:<br>        return None<br>    arc_length = (pi_value * diameter) * (angle / 360)<br>    return arc_length<br></code>                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | <code>1.0</code> |
  | <code>def to_uppercase(input_string: str) -> str:<br>    """<br>    Convert the given string to uppercase.<br><br>    Parameters:<br>    input_string (str): The string to be converted to uppercase.<br><br>    Returns:<br>    str: The uppercase version of the input string. If the input is not a string, returns None.<br>    """<br>    # Check if the input is a string<br>    if not isinstance(input_string, str):<br>        print("Error: Input must be a string.")<br>        return None<br><br>    # Use the built-in upper() method to convert the string to uppercase<br>    return input_string.upper()<br><br># Example usage and testing<br>if __name__ == "__main__":<br>    # Test cases<br>    test_cases = [<br>        "hello world",  # Normal case<br>        "Python is Fun",  # Mixed case<br>        "12345",  # Numeric string<br>        "",  # Empty string<br>        123,  # Non-string input<br>        ["This", "is", "a", "list"],  # Non-string input<br>    ]<br><br>    for test in test_cases:<br>        result = to_uppercase(test)<br>        print(f"Input: {test}")<br>        print(f"Output: {re...</code> | <code>def convert_to_uppercase(text):<br>    uppercase_text = ''<br>    for char in text:<br>        if 'a' <= char <= 'z':<br>            uppercase_text += chr(ord(char) - 32)<br>        else:<br>            uppercase_text += char<br>    return uppercase_text<br></code>                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | <code>1.0</code> |
* Loss: [<code>CosineSimilarityLoss</code>](https://sbert.net/docs/package_reference/sentence_transformer/losses.html#cosinesimilarityloss) with these parameters:
  ```json
  {
      "loss_fct": "torch.nn.modules.loss.MSELoss"
  }
  ```

### Training Hyperparameters
#### Non-Default Hyperparameters

- `eval_strategy`: steps
- `per_device_train_batch_size`: 16
- `per_device_eval_batch_size`: 16
- `multi_dataset_batch_sampler`: round_robin

#### All Hyperparameters
<details><summary>Click to expand</summary>

- `overwrite_output_dir`: False
- `do_predict`: False
- `eval_strategy`: steps
- `prediction_loss_only`: True
- `per_device_train_batch_size`: 16
- `per_device_eval_batch_size`: 16
- `per_gpu_train_batch_size`: None
- `per_gpu_eval_batch_size`: None
- `gradient_accumulation_steps`: 1
- `eval_accumulation_steps`: None
- `torch_empty_cache_steps`: None
- `learning_rate`: 5e-05
- `weight_decay`: 0.0
- `adam_beta1`: 0.9
- `adam_beta2`: 0.999
- `adam_epsilon`: 1e-08
- `max_grad_norm`: 1
- `num_train_epochs`: 3
- `max_steps`: -1
- `lr_scheduler_type`: linear
- `lr_scheduler_kwargs`: {}
- `warmup_ratio`: 0.0
- `warmup_steps`: 0
- `log_level`: passive
- `log_level_replica`: warning
- `log_on_each_node`: True
- `logging_nan_inf_filter`: True
- `save_safetensors`: True
- `save_on_each_node`: False
- `save_only_model`: False
- `restore_callback_states_from_checkpoint`: False
- `no_cuda`: False
- `use_cpu`: False
- `use_mps_device`: False
- `seed`: 42
- `data_seed`: None
- `jit_mode_eval`: False
- `bf16`: False
- `fp16`: False
- `fp16_opt_level`: O1
- `half_precision_backend`: auto
- `bf16_full_eval`: False
- `fp16_full_eval`: False
- `tf32`: None
- `local_rank`: 0
- `ddp_backend`: None
- `tpu_num_cores`: None
- `tpu_metrics_debug`: False
- `debug`: []
- `dataloader_drop_last`: False
- `dataloader_num_workers`: 0
- `dataloader_prefetch_factor`: None
- `past_index`: -1
- `disable_tqdm`: False
- `remove_unused_columns`: True
- `label_names`: None
- `load_best_model_at_end`: False
- `ignore_data_skip`: False
- `fsdp`: []
- `fsdp_min_num_params`: 0
- `fsdp_config`: {'min_num_params': 0, 'xla': False, 'xla_fsdp_v2': False, 'xla_fsdp_grad_ckpt': False}
- `fsdp_transformer_layer_cls_to_wrap`: None
- `accelerator_config`: {'split_batches': False, 'dispatch_batches': None, 'even_batches': True, 'use_seedable_sampler': True, 'non_blocking': False, 'gradient_accumulation_kwargs': None}
- `parallelism_config`: None
- `deepspeed`: None
- `label_smoothing_factor`: 0.0
- `optim`: adamw_torch_fused
- `optim_args`: None
- `adafactor`: False
- `group_by_length`: False
- `length_column_name`: length
- `project`: huggingface
- `trackio_space_id`: trackio
- `ddp_find_unused_parameters`: None
- `ddp_bucket_cap_mb`: None
- `ddp_broadcast_buffers`: False
- `dataloader_pin_memory`: True
- `dataloader_persistent_workers`: False
- `skip_memory_metrics`: True
- `use_legacy_prediction_loop`: False
- `push_to_hub`: False
- `resume_from_checkpoint`: None
- `hub_model_id`: None
- `hub_strategy`: every_save
- `hub_private_repo`: None
- `hub_always_push`: False
- `hub_revision`: None
- `gradient_checkpointing`: False
- `gradient_checkpointing_kwargs`: None
- `include_inputs_for_metrics`: False
- `include_for_metrics`: []
- `eval_do_concat_batches`: True
- `fp16_backend`: auto
- `push_to_hub_model_id`: None
- `push_to_hub_organization`: None
- `mp_parameters`: 
- `auto_find_batch_size`: False
- `full_determinism`: False
- `torchdynamo`: None
- `ray_scope`: last
- `ddp_timeout`: 1800
- `torch_compile`: False
- `torch_compile_backend`: None
- `torch_compile_mode`: None
- `include_tokens_per_second`: False
- `include_num_input_tokens_seen`: no
- `neftune_noise_alpha`: None
- `optim_target_modules`: None
- `batch_eval_metrics`: False
- `eval_on_start`: False
- `use_liger_kernel`: False
- `liger_kernel_config`: None
- `eval_use_gather_object`: False
- `average_tokens_across_devices`: True
- `prompts`: None
- `batch_sampler`: batch_sampler
- `multi_dataset_batch_sampler`: round_robin
- `router_mapping`: {}
- `learning_rate_mapping`: {}

</details>

### Training Logs
| Epoch  | Step | Training Loss | skyoj-val_cosine_ap |
|:------:|:----:|:-------------:|:-------------------:|
| 0.3879 | 500  | 0.0564        | 0.9918              |
| 0.7758 | 1000 | 0.0265        | 0.9948              |
| 1.0    | 1289 | -             | 0.9950              |
| 1.1637 | 1500 | 0.0164        | 0.9955              |
| 1.5516 | 2000 | 0.0116        | 0.9958              |
| 1.9395 | 2500 | 0.0119        | 0.9968              |
| 2.0    | 2578 | -             | 0.9967              |
| 2.3274 | 3000 | 0.0085        | 0.9964              |
| 2.7153 | 3500 | 0.0078        | 0.9969              |
| 3.0    | 3867 | -             | 0.9970              |


### Framework Versions
- Python: 3.10.19
- Sentence Transformers: 5.2.0
- Transformers: 4.57.3
- PyTorch: 2.9.1+cu128
- Accelerate: 1.12.0
- Datasets: 4.4.2
- Tokenizers: 0.22.1

## Citation

### BibTeX

#### Sentence Transformers
```bibtex
@inproceedings{reimers-2019-sentence-bert,
    title = "Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks",
    author = "Reimers, Nils and Gurevych, Iryna",
    booktitle = "Proceedings of the 2019 Conference on Empirical Methods in Natural Language Processing",
    month = "11",
    year = "2019",
    publisher = "Association for Computational Linguistics",
    url = "https://arxiv.org/abs/1908.10084",
}
```

<!--
## Glossary

*Clearly define terms in order to be accessible across audiences.*
-->

<!--
## Model Card Authors

*Lists the people who create the model card, providing recognition and accountability for the detailed work that goes into its construction.*
-->

<!--
## Model Card Contact

*Provides a way for people who have updates to the Model Card, suggestions, or questions, to contact the Model Card authors.*
-->