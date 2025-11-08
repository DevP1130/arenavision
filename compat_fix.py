"""
Compatibility fix for Python 3.9 with Google Cloud libraries.

This fixes the 'importlib.metadata' has no attribute 'packages_distributions' error
by adding a compatibility shim for Python 3.9.
"""
import sys
import importlib.metadata

# Python 3.9 compatibility: packages_distributions was added in Python 3.10
if sys.version_info < (3, 10) and not hasattr(importlib.metadata, 'packages_distributions'):
    def _packages_distributions():
        """
        Compatibility shim for packages_distributions in Python 3.9.
        
        Returns a mapping of top-level import names to their distribution names.
        This is a simplified version that works for most cases.
        """
        try:
            # Try to get a basic mapping from installed packages
            result = {}
            # This is a simplified implementation - the real one in Python 3.10+
            # is more complex, but this should work for Google Cloud libraries
            for dist in importlib.metadata.distributions():
                try:
                    # Get top-level names from the distribution
                    if dist.files:
                        for file in dist.files:
                            if file.parts:
                                top_level = file.parts[0]
                                if top_level not in result:
                                    result[top_level] = []
                                if dist.metadata['Name'] not in result[top_level]:
                                    result[top_level].append(dist.metadata['Name'])
                except Exception:
                    continue
            return result
        except Exception:
            # Fallback: return empty dict if anything fails
            # This is safe - Google Cloud libraries can work without it
            return {}
    
    # Monkey patch the missing attribute
    importlib.metadata.packages_distributions = _packages_distributions

