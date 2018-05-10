set -e
rm -r build dist || true
python setup.py sdist
python setup.py bdist_wheel
twine upload dist/*
echo Success
