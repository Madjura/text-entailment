from django import forms


class QueryForm(forms.Form):
    """Form used to initiate the training of a classifier."""
    query = forms.CharField(label="Query")
    min_relatedness = forms.FloatField(label="Minimum relatdness in graph navigation", initial=0.25, min_value=0.0,
                                       max_value=1.0)
    max_path_length = forms.IntegerField(label="Maximum path length", initial=5)
    max_paths = forms.IntegerField(label="Maximum number of paths", initial=3)