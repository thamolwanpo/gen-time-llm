# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/utils.ipynb.

# %% auto 0
__all__ = ['fake', 'generate_fake_data']

# %% ../nbs/utils.ipynb 2
import pandas as pd
import numpy as np
import random
from faker import Faker

# Initialize Faker to generate random fake data
fake = Faker()

# %% ../nbs/utils.ipynb 5
# Function to generate random time series data for each row
def generate_fake_data(n_series: int,
                       min_length: int = 10,
                       n_temporal_features: int = 5,
                       policy_sectors: list = None,
                       mode: str = 'train',
                       seed: int = 42) -> list:
    """
    Generate Synthetic Time Series Data with Temporal and Static Features for Each Row.

    This function generates synthetic time series data for multiple series with random features and metadata. 
    Each time series has a fixed length (default 10), and for each series, a number of temporal features 
    (randomly generated integers or floats) and static metadata are created. The generated data is intended to 
    simulate a panel dataset, where each time series belongs to a different "entity" (e.g., country, region, or 
    document), and can be used for tasks such as data analysis, machine learning, or simulation testing.

    **Parameters:**
    - `n_series` (int): 
        The number of time series to generate. This defines how many independent series or rows will be created in 
        the dataset. Each series will represent an individual entity (e.g., a different country or document).
    
    - `min_length` (int, default=10): 
        The fixed length of each time series, representing the number of temporal data points. By default, each 
        time series will contain 10 time points, which could represent years, months, or other time units.

    - `n_temporal_features` (int, default=5): 
        The number of temporal features to generate for each time series. These features will vary over time and 
        are randomly generated as either integers or floats. Temporal features represent any additional dynamic 
        information associated with the entity over time, such as varying economic indicators, weather patterns, 
        or other exogenous factors.

    - `policy_sectors` (list, optional): 
        A list of sector labels that are used to randomly assign one or more sectors to each time series. 
        These could represent industries, fields of work, or areas of policy (e.g., 'Agriculture', 'Energy', 
        'Transport'). If no list is provided, a default list of policy sectors is used.

    - `mode` (str, default='train'): 
        Specifies the mode of the generated data, either 'train' or 'test'. 
        In 'train' mode, a simplified dictionary is created without additional identifiers. 
        In 'test' mode, additional metadata (e.g., document IDs, country names) is included in the returned 
        data for evaluation or testing purposes.

    - `seed` (int, default=42): 
        A random seed value for reproducibility. By setting a seed, the random data generated will be the same 
        each time the function is run, which is useful for consistency in experiments and debugging.

    **Returns:**
    - A list of dictionaries, where each dictionary contains the following fields:
        - `'doc_id'`: A randomly generated UUID to represent the unique identifier of a document (only in test mode).
        - `'sector'`: A string representing the randomly assigned sectors (either in single or multi-label format).
        - `'country'`: A randomly generated country name to represent the geography associated with the series 
                      (only in test mode).
        - `'anchor_summary'`: A randomly generated sentence that acts as a short description or summary for each 
                              document or entity (only in test mode).
        - `'positive_time_series'`: A 2D list representing the time series data. Each row corresponds to one time 
                                    point in the series, and each column is a different temporal feature.
        - `'positive_sector'`: A one-hot encoded list representing the sector(s) assigned to this time series. 
                               The length of the list is equal to the number of sectors provided.
        - `'columns'`: A list of the names of the temporal features (e.g., ['temporal_0', 'temporal_1', ..., 
                     'temporal_n']).

    **Example Usage:**

    ```python
    policy_sectors = ['Agriculture', 'Energy', 'Transport', 'Health', 'Finance', 'Education']
    synthetic_data = generate_fake_data(n_series=100, n_temporal_features=2, policy_sectors=policy_sectors, mode='train')
    ```

    In the example above, the function will generate 100 synthetic time series, each with 10 temporal points 
    and 5 temporal features, and randomly assigned sectors. The data can then be used for training machine 
    learning models, testing algorithms, or running simulations in different scenarios.

    **Notes:**
    - The temporal features are generated as a mix of random integers and floats to simulate a diverse dataset.
    - The metadata generated, such as document IDs, country names, and summaries, are completely synthetic and 
      randomly generated, making this data useful for experimentation without relying on real-world sensitive 
      information.
    - The structure and format of the output data can be extended or modified depending on the specific use case.
    """

    # Initialize random state for reproducibility
    rng = np.random.RandomState(seed)
    
    if policy_sectors is None:
        policy_sectors = ['Agriculture', 'Energy', 'Transport', 'Health', 'Finance', 'Education']
    
    processed_data = []
    
    for idx in range(n_series):
        # Generate random "Geography" (fake country names)
        geography = fake.country()
        
        # Generate random document ID
        document_id = fake.uuid4()
        
        # Generate random family summary (random sentence)
        family_summary = fake.sentence()
        
        # Generate a random year as the last event in the timeline
        last_event_year = rng.randint(1990, 2025)
        year_range = list(range(last_event_year - min_length + 1, last_event_year + 1))
        
        # Generate random time series data (10-year history)
        time_series_df = pd.DataFrame({'year': year_range})
        
        # Generate temporal features
        for i in range(n_temporal_features):
            # Randomly choose whether to generate integers or floats for each temporal feature
            if rng.rand() > 0.5:
                # Generate random integers between 0 and 100
                time_series_df[f'temporal_{i}'] = rng.randint(0, 100, size=len(time_series_df))
            else:
                # Generate random floats between 0 and 100
                time_series_df[f'temporal_{i}'] = rng.uniform(0, 100, size=len(time_series_df))
        
        # Drop 'year' for time series array
        time_series_columns = time_series_df.drop(columns=['year']).columns.tolist()
        time_series_np = time_series_df.drop(columns=['year']).to_numpy()
        
        # One-hot encode sectors: randomly choose sectors for this row
        selected_sectors = random.sample(policy_sectors, rng.randint(1, len(policy_sectors)))
        one_hot_encoding = np.zeros(len(policy_sectors), dtype=int)
        for sector in selected_sectors:
            one_hot_encoding[policy_sectors.index(sector)] = 1

        # Append the processed data
        if mode == 'test':
            processed_data.append({
                'doc_id': document_id,
                'sector': ';'.join(selected_sectors),
                'country': geography,
                'anchor_summary': family_summary,
                'positive_time_series': time_series_np.tolist(),
                'positive_sector': one_hot_encoding.tolist(),
                'columns': time_series_columns  # Add column names here
            })
        else:
            processed_data.append({
                'anchor_summary': family_summary,
                'positive_time_series': time_series_np,
                'positive_sector': one_hot_encoding.tolist(),
                'sector': ';'.join(selected_sectors),
                'country': geography,
                'columns': time_series_columns  # Add column names here
            })

    return processed_data
